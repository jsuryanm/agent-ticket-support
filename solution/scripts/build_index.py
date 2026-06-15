import sys
from pathlib import Path

if __package__ in {None, ""}:
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from solution.config import settings
from solution.agentic.tools.vector_store import get_vectorstore
from solution.data.models import udahub

config = settings()

def main() -> None:
    load_dotenv()
    engine = create_engine(f"sqlite:///{config.UDAHUB_DB}", echo=False)
    session = sessionmaker(bind=engine)()
    try:
        articles = session.query(udahub.Knowledge).all()
        texts = [f"{a.title}\n\n{a.content}" for a in articles]
        # Store title/tags as metadata so retrieval results carry their source.
        metadatas = [{"title": a.title, "tags": a.tags or ""} for a in articles]
        ids = [a.article_id for a in articles]
    finally:
        session.close()

    store = get_vectorstore(config.knowledge_base)
    store.add_texts(texts=texts, metadatas=metadatas, ids=ids)
    print(f"✅ Indexed {len(texts)} articles into '{config.knowledge_base}' at {config.INDEX_DIR}")


if __name__ == "__main__":
    main()
