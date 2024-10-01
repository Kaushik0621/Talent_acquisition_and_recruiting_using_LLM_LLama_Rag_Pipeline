import os
import json
import pandas as pd
from dotenv import load_dotenv
from llama_index.core import Document, VectorStoreIndex
import openai

# Load environment variables
load_dotenv()

# Set OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    openai.api_key = api_key
else:
    raise ValueError("OpenAI API key is not set. Check your .env file.")

def process_json_with_llm(json_path: str, job_description: str):
    """
    Process the JSON file, send it to the LLM along with a scoring prompt, and return the LLM's response in a structured JSON format.
    
    Args:
        json_path (str): The path to the JSON file.
        job_description (str): The job description to be provided to the LLM for scoring.
        
    Returns:
        dict: The response in the format provided by the LLM, which includes a score and explanation for each category.
    """
    # Load the JSON data
    with open(json_path, "r") as json_file:
        candidate_data = json.load(json_file)

    # Convert the JSON data into a Document (expected by the LLM)
    candidate_document = Document(text=json.dumps(candidate_data))

    # Create an index and query engine
    index = VectorStoreIndex.from_documents(documents=[candidate_document])
    query_engine = index.as_query_engine()

    # Prepare the prompt to instruct the LLM on how to score the candidate
    prompt = f"""
    You are tasked with scoring a candidate for the following job description:
    {job_description}

    The candidate's details are provided in the attached JSON. Your task is to evaluate the candidate based on a detailed set of criteria:

    1. **Work Experience (40 points)** - Assess the candidate's work experience based on the following:
        a. **Relevance (15 points)** - How closely does the candidate's work experience align with the key responsibilities, industry, and domain of the job description? If the experience is not relevant, this section should receive a very low score regardless of the duration or achievements, can also score Zero. 
        But if the relevance is matching with the {job_description}, it should be rewarded with high score.
        b. **Duration (10 points)** - Evaluate the duration of the candidate's experience, but consider that duration should not compensate for a lack of relevance. If the experience is not in the same field or industry, the score here should also be zero.
        c. **Achievements (10 points)** - Consider significant achievements only if they are relevant to the job’s domain and responsibilities. Achievements in unrelated fields should be weighted much less.
        d. **Career Progression (5 points)** - Evaluate the candidate’s career progression within the relevant field. If the progression is in an unrelated field, reduce the score accordingly.

    2. **Education (30 points)** - Evaluate the candidate's educational background considering:
        a. **Relevance of Degree (15 points)** - How well does the candidate's degree or field of study align with the job requirements? A degree in an unrelated field should result in a lower score.
        b. **Institution and Qualification Level (10 points)** - Consider the reputation of the institution and the level of qualification, but relevance to the job should take precedence.
        c. **Additional Certifications or Training (5 points)** - Evaluate additional certifications or training, with an emphasis on relevance to the job description. Certifications in unrelated areas should be scored lower.

    3. **Skills (30 points)** - Assess the candidate's skills based on:
        a. **Core Skills (15 points)** - How well do the candidate's core skills align with the required skills in the job description? If the core skills are not relevant, the score should be very low.
        b. **Technical Skills (10 points)** - Evaluate technical skills only if they are directly relevant to the job. Irrelevant technical skills should not contribute significantly to the score and will get a zero to five.
        c. **Soft Skills (5 points)** - Assess soft skills, but consider them less important if the candidate lacks relevant core and technical skills.

    Please score the candidate out of 100 based on these criteria and provide a detailed explanation of the score for each section (work experience, education, skills), including why the candidate received that specific score.

    It is crucial that relevance to the job description is the primary factor in scoring. If the candidate's experience, education, or skills are not relevant to the job description, their scores in these categories should be significantly reduced, regardless of other factors.

    Return the result in JSON format with the following structure:
    {{
        "Work EX": {{
            "marks": int,
            "description": str
        }},
        "Education": {{
            "marks": int,
            "description": str
        }},
        "Relevant Skills": {{
            "marks": int,
            "description": str
        }},
        "total_marks": {{
            "marks": int,
            "description": str
        }}
    }}
"""

    # Send the prompt to the LLM for scoring
    response = query_engine.query(prompt)
    
    # Parse the LLM's response (assuming response format is structured correctly)
    llm_output = response.response
    
    # The LLM's response should be a structured JSON as specified in the prompt
    result = json.loads(llm_output)
    
    return result


def process_folder_of_json(folder_path: str, job_description: str):
    """
    Process all JSON files in a folder and get the LLM to score each candidate based on the job description.
    
    Returns:
        dict: A dictionary containing the results for all JSON files in the folder.
    """
    all_results = {}
    
    # Loop through all files in the folder
    for filename in os.listdir(folder_path):
        if filename.endswith(".json"):  # Only process JSON files
            json_path = os.path.join(folder_path, filename)
            
            try:
                # Send the candidate's data and job description to the LLM for scoring
                llm_response = process_json_with_llm(json_path, job_description)
                
                # Store the LLM's response for each candidate by filename
                all_results[filename] = llm_response
                
            except Exception as e:
                # Handle any errors during processing
                all_results[filename] = {"error": str(e)}
    
    return all_results

def save_candidate_response(candidate_data, output_file):
    """
    Save the candidate response to a JSON file.
    
    Args:
        candidate_data (dict): Dictionary containing candidate results.
        output_file (str): Path to save the JSON file.
    """
    with open(output_file, "w") as f:
        json.dump(candidate_data, f, indent=4)
    
def sort_and_save_candidates(candidate_data, output_csv_file):
    """
    Sort candidates by total marks and save the results to a CSV file.
    
    Args:
        candidate_data (dict): Dictionary containing candidate results.
        output_csv_file (str): Path to save the resulting CSV file.
        
    Returns:
        DataFrame: Sorted DataFrame of candidates by total marks.
    """
    # Extract candidate information into a list
    candidate_list = [
        {
            "Filename": filename,
            "Work EX Marks": data["Work EX"]["marks"],
            "Education Marks": data["Education"]["marks"],
            "Relevant Skills Marks": data["Relevant Skills"]["marks"],
            "Total Marks": data["total_marks"]["marks"]
        }
        for filename, data in candidate_data.items() if "total_marks" in data
    ]
    
    # Convert to DataFrame
    df = pd.DataFrame(candidate_list)
    
    # Sort by total marks in descending order
    df_sorted = df.sort_values(by="Total Marks", ascending=False)
    
    # Save to CSV
    df_sorted.to_csv(output_csv_file, index=False)
    
    return df_sorted
