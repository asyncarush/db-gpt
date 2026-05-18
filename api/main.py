import redis
from agent.graph import agent


def main():
    question = "Identify product categories with high review scores but unusually high delivery delays."

    for step in agent.stream(
        {"messages": [{"role": "user", "content": question}]},
        stream_mode="values",
        config={"recursion_limit": 20},  # add this
    ):
        step["messages"][-1].pretty_print()


if __name__ == "__main__":
    main()