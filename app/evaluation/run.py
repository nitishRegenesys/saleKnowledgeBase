from app.evaluation.questions import QUESTIONS
from app.rag.answer import answer_question


def run_evaluation():
    print("=" * 100)
    print("RAG EVALUATION")
    print("=" * 100)

    total = len(QUESTIONS)

    for index, question in enumerate(QUESTIONS, 1):

        print()
        print("=" * 100)
        print(f"QUESTION {index}/{total}")
        print("=" * 100)
        print(question)

        try:
            result = answer_question(
                question,
                limit=10,
            )

        except Exception as exc:
            print()
            print("STATUS: FAILED")
            print("ERROR:", type(exc).__name__, str(exc))
            continue

        print()
        print("FILTER:")
        print(
            "  CATEGORY:",
            result.get("category_filter"),
        )
        print(
            "  SUBCATEGORY:",
            result.get("subcategory_filter"),
        )

        print()
        print("ANSWER:")
        print(result["answer"])

        print()
        print("RETRIEVED RESULTS:")

        for rank, retrieved in enumerate(
            result["results"],
            1,
        ):
            print(
                f"  {rank}. "
                f"{retrieved.title} | "
                f"{retrieved.category} | "
                f"{retrieved.subcategory or '-'} | "
                f"score={retrieved.hybrid_score:.4f}"
            )

        print()
        print("SOURCES:")

        for source in result["sources"]:
            print(
                f"  - {source['title']} | "
                f"{source['category']} | "
                f"{source['subcategory'] or '-'}"
            )

        print()
        print("STATUS: OK")


if __name__ == "__main__":
    run_evaluation()