import logging
from pathlib import Path
from ai.vector_index import VectorIndex

# ==============================
# Logging
# ==============================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | BUILD_PIPELINE | %(message)s"
)

logger = logging.getLogger("BUILD_PIPELINE")

# ==============================
# Pipeline
# ==============================

class BuildIndexPipeline:
    def __init__(self):
        self.index_engine = VectorIndex()

    # --------------------------
    # Sanity checks
    # --------------------------
    def _precheck(self):
        logger.info("Running pre-checks...")

        data_path = Path("data/processed/processed_catalogue.json")
        if not data_path.exists():
            raise FileNotFoundError(f"Missing processed data: {data_path}")

        logger.info("Pre-checks passed ✅")

    # --------------------------
    # Build
    # --------------------------
    def build(self):
        logger.info("Starting vector index build pipeline...")

        self._precheck()

        self.index_engine.build()

        logger.info("Vector build completed successfully ✅")

    # --------------------------
    # Validation
    # --------------------------
    def validate(self):
        logger.info("Running validation queries...")

        self.index_engine.load()

        test_queries = [
            "java",
            "python",
            "sql",
            "data science",
            "machine learning",
            "aptitude test",
            "cognitive ability",
            "english test",
            "logical reasoning",
            "software engineer",
        ]

        for q in test_queries:
            results = self.index_engine.search(q, top_k=5)
            logger.info(f"\nQUERY: {q}")
            for r in results[:3]:
                logger.info(f"  - {r.get('name')} | score={round(r.get('score',0),4)}")

        logger.info("Validation completed ✅")

    # --------------------------
    # Full pipeline
    # --------------------------
    def run(self):
        self.build()
        self.validate()


# ==============================
# Entrypoint
# ==============================
if __name__ == "__main__":
    pipeline = BuildIndexPipeline()
    pipeline.run()