import os
from openai import AsyncOpenAI, LengthFinishReasonError
from .prompts import *
from .schemas import InterviewerResponseSchema, ExtractedActionsSchema, RoleListSchema, ThemeSummarySchema

CHAT_MODEL = os.environ.get('OPENAI_CHAT_MODEL')
ANALYSIS_MODEL = os.environ.get('OPENAI_ANALYSIS_MODEL')
EMBEDDING_MODEL = os.environ.get('OPENAI_EMBEDDING_MODEL')

client = None


def get_client():
    global client
    if client is None:
        client = AsyncOpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
    return client


async def generate_roles(company_description: str):
    client = get_client()
    response = await client.beta.chat.completions.parse(model=CHAT_MODEL,
                                                        messages=[{"role": "system", "content": "Generate employee roles for a company."},
                                                                  {"role": "user", "content": ROLE_GENERATION_PROMPT.format(company=company_description)}],
                                                        response_format=RoleListSchema)
    return response.choices[0].message.parsed.roles[:10]


async def run_single_interview(company_description: str, role: str, interview_number: int, max_turns: int):
    client = get_client()
    
    conversation = []
    prefix = f"Interview {interview_number} - {role}"

    for turn in range(1, max_turns + 2):

        # Interviewer turn (structured output)
        i_messages = [{"role": "system", "content": INTERVIEWER_SYSTEM_PROMPT.format(company=company_description, turn_count=turn, max_turns=max_turns)}]
        for msg in conversation:
            r = "assistant" if msg["role"] == "interviewer" else "user"
            i_messages.append({"role": r, "content": msg["content"]})
        
        if turn > max_turns: # Hard stop: Terminate if max turns are reached.
            conversation.append({"role": "interviewer", "content": "Thank you for your time. This concludes the interview."})
            return conversation

        try:
            response = await client.beta.chat.completions.parse(model=CHAT_MODEL, 
                                                                messages=i_messages, 
                                                                response_format=InterviewerResponseSchema,
                                                                reasoning_effort="minimal")
            parsed = response.choices[0].message.parsed
        except LengthFinishReasonError:
            print(f"{prefix} Turn {turn}/{max_turns} | token limit reached, ending interview")
            break
        conversation.append({"role": "interviewer", "content": parsed.message})

        # print(f"{prefix} Turn {turn}/{max_turns} | complete={parsed.is_interview_complete} | Q: {parsed.message[:50]}")
        if parsed.is_interview_complete: # Terminate if interviewer signals completion or max turns reached
            conversation[-1]["content"] = "Thank you for your time. This concludes the interview."
            break

        # Employee turn
        e_messages = [{"role": "system", "content": EMPLOYEE_SYSTEM_PROMPT.format(company=company_description, role=role)}]
        for msg in conversation:
            r = "assistant" if msg["role"] == "employee" else "user"
            e_messages.append({"role": r, "content": msg["content"]})

        response = await client.chat.completions.create(model=CHAT_MODEL, 
                                                        messages=e_messages,
                                                        reasoning_effort="minimal")
        answer = response.choices[0].message.content
        conversation.append({"role": "employee", "content": answer})
        # print(f"{prefix} Turn {turn}/{max_turns} | A: {answer[:50]}")

    print(f"{prefix} - Done with {len(conversation)} messages. max_turns={max_turns}")
    return conversation


async def extract_actions(conversation_messages: list[dict]):
    client = get_client()
    conv_text = "\n".join(f"{m['role'].title()}: {m['content']}" for m in conversation_messages) # Interviewer: ... \n Employee: ...
    # try:
    response = await client.beta.chat.completions.parse(model=CHAT_MODEL,
                                                        messages=[{"role": "system", "content": ACTION_EXTRACTION_SYS_PROMPT},
                                                                  {"role": "user", "content": ACTION_EXTRACTION_PROMPT.format(conversation=conv_text)}],
                                                        response_format=ExtractedActionsSchema)
    return [{"action": a.action, "quote": a.quote} for a in response.choices[0].message.parsed.actions]


async def get_embeddings(texts: list[str]):
    client = get_client()
    response = await client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]


async def summarize_theme(action_items: list[dict]) -> ThemeSummarySchema:
    client = get_client()
    formatted = "\n".join(f"- {a['action']} (Employee: \"{a['quote']}\")" for a in action_items)
    response = await client.beta.chat.completions.parse(model=ANALYSIS_MODEL,
                                                        messages=[{"role": "system", "content": THEME_SUMMARY_SYS_PROMPT},
                                                                  {"role": "user", "content": THEME_SUMMARY_PROMPT.format(actions=formatted)}],
                                                        response_format=ThemeSummarySchema)
    return response.choices[0].message.parsed
