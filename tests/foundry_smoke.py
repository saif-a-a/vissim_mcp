import os

ENDPOINT = "https://vismcp-resource.services.ai.azure.com/openai/v1"
DEPLOYMENT_NAME = "gpt-5"


def main():
    from openai import OpenAI

    client = OpenAI(
        base_url=ENDPOINT,
        api_key=os.environ["AZURE_AI_SERVICES_KEY"],
    )
    response = client.responses.create(
        model=DEPLOYMENT_NAME,
        input="What is the capital of France?",
    )

    print(f"answer: {response.output[0]}")


if __name__ == "__main__":
    main()