import gradio as gr
from utils.logger import logger
from clients.llm_client import encode_query, construct_prompt
from clients.opensearch_client import OpenSearchClient
from clients.kubernetes_client import generate_response_with_kubectl

opensearch_client = OpenSearchClient()

# Create the chatbot interface that will be called.
def chatbot_interface(user_input, model_choice, index_date):
    """
    Handles the chatbot interface logic, processes the user query, retrieves relevant documents,
    constructs a prompt for the selected model, and returns the response.

    Parameters:
        user_input (str): The user's input query.
        model_choice (str): The selected model for generating the response ("Claude Sonnet" or "TO.DO").
        index_date (datetime): The date for which to query the logs, used to form the index name.

    Returns:
        str: The model's response to the user's query, or an error message if no match is found.
    """
    # Transform to the desired format YYYYMMDD
    formatted_date = index_date.strftime("%Y%m%d")
    index_name = f"eks-cluster-{formatted_date}"
    logger.info(f"Received user query for date: {index_date}, model: {model_choice}, and user input:\n {user_input}\n")
    query_embedding = encode_query(user_input)

    retrieved_docs = opensearch_client.retrieve_documents(query_embedding=query_embedding, index_name=index_name)

    if retrieved_docs is not None:
        prompt = construct_prompt(query=user_input, retrieved_docs=retrieved_docs)
        # Choose the model based on the combo box selection
        if model_choice == "Claude Sonnet":
            response = generate_response_with_kubectl(prompt, "claude")
        else:
            response = "Invalid model selection"
        return response
    else:
        return "No match for the prompt found in the vector database!"


def create_interface():
    """
    Creates and returns the Gradio interface for the chatbot, including UI elements like the date picker,
    model selection dropdown, user input textbox, and output area.
    """
    with gr.Blocks(css=".container { max-width: 700px; margin: auto; padding-top: 20px; }") as demo:
        gr.Markdown(
            """
            <div style="text-align: center;">
                <h1>Document Retrieval Chatbot</h1>
            </div>
            """
        )

        with gr.Row():
            with gr.Column():
                index_date = gr.DateTime(
                    label="Select Date",
                    type="datetime",
                    include_time=False,
                    info="Select the date to query logs"
                )

                # Add the model selection combo box
                model_dropdown = gr.Dropdown(
                    choices=["Claude Sonnet", "TODO"],
                    value="Claude Sonnet",
                    label="Select Model"
                )

                user_input = gr.Textbox(
                    label="Your Question",
                    placeholder="Type your question here..."
                )
                submit_button = gr.Button("Submit")

            with gr.Column():
                output = gr.Markdown(label="Response")

        submit_button.click(
            fn=chatbot_interface,
            inputs=[user_input, model_dropdown, index_date],
            outputs=output
        )

    return demo


if __name__ == "__main__":
    logger.info("Starting Gradio interface...")
    interface = create_interface()
    interface.launch()
    logger.info("Gradio interface launched successfully.")
    