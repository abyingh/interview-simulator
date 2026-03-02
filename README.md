# Interview Simulator App

An AI-powered employee interview simulation platform. An interviewer chatbot conducts interviews with employee chatbots acting as various roles within a company, then analyzes responses to surface the most critical strategic insights for leadership. The app;

1. Lets you define a company description
2. Generates relevant employee roles based on the company context (LLM)
3. Runs 100 simulated interviews between interviewer and employees and stores all interview threads in the database
4. After interviews complete, it performs an automated analysis and displays the top 3 most important themes, including direct supporting employee quotes (LLM + embeddings + clustering)
5. Saves the interview data and results to the database (view the full conversation thread by selecting an interview in the dropdown menu below)
6. Generates a simple downloadable presentation (board deck) summarizing the key themes and recommended focus areas.
   - Slide 1: Title
   - Slide 2: Top 3 Strategic Priorities
   - Slide 3: Deep Dive on #1 Priority
   - Slide 4: Methodology & Participants
   

## Project Structure
```
Interview Simulator App/
│
├── manage.py                                # Entry point to run Django commands
├── requirements.txt                         # Python requirements
├── entrypoint.sh                            # Startup script for Docker container
│
├── config/                                  # Django configurations
│   ├── __init__.py                          
│   ├── settings.py                          # Django settings
│   ├── urls.py                              # URL routing
│   └── wsgi.py                              # WSGI for production
│
├── app/                                     # Django app
│   ├── __init__.py                          
│   ├── models.py                            # Database table definitions
│   ├── views.py                             # Request handlers
│   ├── urls.py                              # URL routes for the app
│   ├── serializers.py                       # Convert python objects to JSON
│   ├── admin.py                             # Register models for admin panel
│   ├── openai_service.py                    # OpenAI API calls
│   ├── prompts.py                           # Prompts for LLMs
│   ├── schemas.py                           # Pydantic models for structured outputs
│   ├── analysis.py                          # Interview analysis
│   ├── board_deck.py                        # Board deck generation (powerpoint)
│   ├── migrations/                          # Database migration scripts
│   └── templates/app/                       # HTML templates for frontend
│       ├── login.html
│       └── dashboard.html
│
├── docker/                                  # Container configuration
│   ├── docker-compose.yml                   # Multi-container Docker app for local running
│   ├── prod.dockerfile                      # Dockerfile for Django app
│   └── prod.dockerfile.dockerignore         # Files to ignore when building the Docker image
│
├── terraform/                               # IaC for Azure deployment
│   ├── main.tf                              # Terraform resources for Azure
│   ├── variables.tf                         # Terraform variables
│   ├── outputs.tf                           # Terraform outputs
│   ├── prod.auto.tfvars.example             # Example non-secret variables
│   ├── secrets.auto.tfvars.example          # Example secret variables
│   ├── deploy.sh                            # Shell script to deploy resources
│   └── destroy.sh                           # Shell script to destroy resources
│
└── tests/                                   # Example unit tests (AI generated)

```


## Workflow
```
Run Interviews -> Extract Actionable Recommendations -> Embed -> Cluster -> Rank -> Generate Board Deck Slides
```


## Tech Stack

- **AI:** OpenAI API
- **Backend:** Django, Django REST Framework
- **Frontend:** Bootstrap, JavaScript
- **Database:** PostgreSQL
- **Infrastructure:** Docker, Terraform, Azure

## How It Works
### Interview Simulation
The interviewer LLM conducts multi-turn interviews with employee LLMs across 10 auto-generated roles. Each interview length is randomized (`max_turns = randint(5, 10)`) to naturally vary the depth of conversation. The current turn count is passed to the interviewer's system prompt via `turn_count` and `max_turns` parameters, allowing it to pace its questions accordingly.


### Analysis Algorithm
1. **Extract**: An LLM extracts actionable recommendations and supporting quotes from each interview using structured responses.
2. **Embed**: Text embeddings are generated for each recommendation and row-wise normalized. After normalization, Euclidean distance becomes mathematically equivalent to cosine similarity, which is the standard metric for comparing text embeddings.
3. **Cluster**: KMeans is applied over a range of $k \in [3, 50]$. The optimal $k$ is selected by the highest Silhouette score, identifying the number of distinct themes.
4. **Rank**: Clusters are ranked by frequency (number of mentions). The top 3 themes are selected.
5. **Summarize**: Each top theme is summarized by an LLM into a named insight with key quotes.
6. **Board Deck**: A `.pptx` presentation is generated with the strategic recommendations.

### Concurrency
To avoid hitting OpenAI rate limits, interviews are run concurrently but capped by `NUM_CONCURRENT_INTERVIEWS` (default: 10) using `asyncio.Semaphore`.


## Local Development
The app runs locally via Docker with 2 services defined in `docker-compose.yml`:

- `db`: PostgreSQL DB
- `web`: Django App

### Setup

```bash
cp .env.example .env  # Populate the required fields
cd docker
docker compose up -d
```

The app will be available at `http://localhost:8000`.

### Shutdown

```bash
docker compose down --rmi local -v
```

## Deployment (Azure)

Deployment is managed via Terraform files in the `terraform/` directory. The main resources provisioned are as follows:

- **Azure Container Apps**: Django App
- **Azure Database for PostgreSQL Flexible Server**: PostgreSQL DB
- **Azure Log Analytics Workspace**: Centralized logging

### Configuration

Copy the example files and fill in your values:

```bash
cd terraform
cp ./prod.auto.tfvars.example ./prod.auto.tfvars # Populate the required fields
cp ./secrets.auto.tfvars.example ./secrets.auto.tfvars  # Populate the required fields
```

#### Variables and Descriptions
**`prod.auto.tfvars`**:  Non-secret deployment variables:

- `project_name`: Project name used for resource naming
- `location`: Azure region
- `resource_group_name`: Azure resource group name
- `subscription_id`: Azure subscription ID
- `docker_image_tag`: Docker image tag to deploy
- `db_port`: PostgreSQL port (default: `5432`) |
- `django_superuser_username`: Django admin username
- `django_superuser_email`: Django admin email
- `openai_chat_model`: Model for interviews and extraction
- `openai_analysis_model`: Model for theme summarization
- `openai_embedding_model`: Model for text embeddings
- `num_interviews`: Number of interviews to simulate (default: `100`)
- `num_concurrent_interviews`: Max concurrent processes: interviews, summarization etc. (default: `10`)
- `postgres_db`: PostgreSQL database name

<br>

**`secrets.auto.tfvars`**: Sensitive variables

- `openai_api_key`: OpenAI API key
- `db_password`: PostgreSQL password 
- `django_secret_key`: Django secret key
- `django_superuser_password`: Django admin password

### Deploy
```bash
cd terraform
bash deploy.sh
```

### Destroy
```bash
cd terraform
bash destroy.sh
```
