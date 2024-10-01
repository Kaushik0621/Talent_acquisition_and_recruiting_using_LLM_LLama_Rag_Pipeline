import gradio as gr
import os
from candidate_score_process import process_folder_of_json, sort_and_save_candidates, save_candidate_response
from config import FOLDER_PATH, OUTPUT_FILE

def candidate_scoring_interface(job_description):
    # Process the folder of JSON files using the provided job description
    candidate_data = process_folder_of_json(FOLDER_PATH, job_description)
    
    # Save the candidate responses to the specified JSON file from config.py
    save_candidate_response(candidate_data, OUTPUT_FILE)
    
    # Sort the candidates and save them to a CSV file
    sorted_candidates = sort_and_save_candidates(candidate_data, "sorted_candidates.csv")
    
    # Get the top 5 candidates
    top_5_candidates = sorted_candidates.head(10)
    
    # Return the top 5 candidates to the Gradio interface
    return top_5_candidates

# Gradio Interface
with gr.Blocks() as demo:
    gr.Markdown("# Candidate Scoring App")
    
    # Input for job description
    job_description_input = gr.Textbox(label="Enter Job Description", lines=10, placeholder="Paste the job description here...")
    
    # Output: Dataframe showing top 5 candidates
    output_dataframe = gr.Dataframe(label="Top 10 Candidates")
    
    # Submit button
    submit_button = gr.Button("Process Candidates")
    
    # Button action
    submit_button.click(
        fn=candidate_scoring_interface, 
        inputs=job_description_input,  # Pass job description input to the function
        outputs=output_dataframe
    )

# Launch the Gradio app
if __name__ == "__main__":
    demo.launch()
