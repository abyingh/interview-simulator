import asyncio, os
import numpy as np
from asgiref.sync import sync_to_async

from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score


from .models import Conversation, ExtractedAction
from .openai_service import extract_actions, get_embeddings, summarize_theme

NUM_CONCURRENT_INTERVIEWS = int(os.environ.get('NUM_CONCURRENT_INTERVIEWS'))


async def extract_items_for_conversation(conv: Conversation, extraction_sem: asyncio.Semaphore) -> list[dict]:
    async with extraction_sem:
        items = await extract_actions(conv.messages) # {action + quote}
        for item in items:
            await sync_to_async(ExtractedAction.objects.create)(conversation=conv, action_text=item["action"])
        print(f"Extraction - {conv.employee_role} - {len(items)} actions")
        
        return items


async def extract_all_items(conversations: list[Conversation]) -> list[dict]:
    extraction_sem = asyncio.Semaphore(min(NUM_CONCURRENT_INTERVIEWS * 3, len(conversations)))
    results = await asyncio.gather(*[extract_items_for_conversation(conv, extraction_sem) for conv in conversations]) # [ [ {action + quote} ] ] for each conversation
    all_items = [item for group in results for item in group] # [ {action + quote} ]
    print(f"Extraction done — {len(all_items)} total actions extracted from {len(conversations)} conversations")
    
    return all_items


async def build_embeddings(action_texts: list[str]) -> list[list[float]]:
    print("\nEmbeddings")
    embeddings = []
    total_batches = (len(action_texts) + 99) // 100
    for i in range(0, len(action_texts), 100):
        batch_num = i // 100 + 1
        batch_size = min(100, len(action_texts) - i)
        # print(f"Embeddings - {batch_num}/{total_batches} ({batch_size} items)")
        batch_emb = await get_embeddings(action_texts[i:i + 100])
        embeddings.extend(batch_emb)
    # print(f"Embeddings done — {len(embeddings)} embeddings in total")

    return embeddings


def normalize_embeddings(embeddings: list[list[float]]) -> np.ndarray:
    X = np.array(embeddings)
    X = X / np.linalg.norm(X, axis=1, keepdims=True) # Row-wise normalization for text embeddings
    print(X.shape)

    return X


def find_best_k(X: np.ndarray, all_items: list[dict]) -> int:
    # Normalization + KMeans with Euclidean distance is mathematically equivalent to cosine similarity (text embeddings should be compared via cosine similarity)
    k_min, k_max = 3, min(50, len(all_items) - 1)
    best_k, best_score = k_min, -1
    # Calculate silhouette score for each k and take the best k
    for k in range(k_min, k_max + 1):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        lbls = km.fit_predict(X)
        score = silhouette_score(X, lbls)
        if score > best_score:
            best_k, best_score = k, score

    print(f"Best n_clusters: {best_k}")

    return best_k


def cluster_items(X: np.ndarray, all_items: list[dict], best_k: int) -> list[tuple[int, list[dict]]]:
    kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X)

    # Group by cluster: {0: [{action, quote}], 1: [{}], ...}
    clusters: dict[int, list[dict]] = {}
    for i, label in enumerate(labels):
        clusters.setdefault(int(label), []).append(all_items[i])

    return sorted(clusters.items(), key=lambda x: len(x[1]), reverse=True) # Sort by cluster size


async def summarize_top_clusters(sorted_clusters: list[tuple[int, list[dict]]]) -> list[dict]:
    # Summarize themes concurrently
    async def summarize_one(idx, items):
        theme = await summarize_theme(items)
        print(f"Summarizing theme: {idx}/{min(3, len(sorted_clusters))} named {theme.theme_name}")
        return {"theme_name": theme.theme_name,
                "summary": theme.summary,
                "key_quotes": theme.key_quotes,
                "action_count": len(items),
                "sample_actions": [item["action"] for item in items[:5]]}

    top_3_clusters = sorted_clusters[:3] # Top 3 only
    
    return await asyncio.gather(*[summarize_one(idx, items) for idx, (n_cluster, items) in enumerate(top_3_clusters, 1)])


async def run_analysis(conversations: list[Conversation], set_status=None) -> list[dict]:
    """Action recommendation extraction -> embedding -> clustering -> theme summarization"""

    print(f"\nAnalysis for {len(conversations)} conversations")

    all_items = await extract_all_items(conversations)

    if not all_items:
        return []

    if set_status:
        await set_status('clustering')

    # Create embeddings from action text
    print("Create embeddings")
    action_texts = [item["action"] for item in all_items]
    embeddings = await build_embeddings(action_texts)

    # K-Means clustering with silhouette score to find optimal k
    print("\nClustering")
    X = normalize_embeddings(embeddings)
    best_k = find_best_k(X, all_items)
    sorted_clusters = cluster_items(X, all_items, best_k)

    if set_status:
        await set_status('summarizing')

    themes = await summarize_top_clusters(sorted_clusters)

    print("\nFinal themes:")
    for i, t in enumerate(themes, 1):
        print(f"  #{i}: {t['theme_name']} ({t['action_count']} mentions)")

    return themes
