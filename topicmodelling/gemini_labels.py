import os
from pydantic import BaseModel
from typing import List
from openai import OpenAI
import pandas as pd



class NamedGroup(BaseModel):
    group_name: str       
    items: List[str]     

class OutputCollection(BaseModel):
    groups: List[NamedGroup]

input_data = pd.read_csv('test.csv')

def get_gemini_labels(csv_name,n_words: int =3):

    input_Data=pd.read_csv(csv_name)
    input_data=input_Data["Representation"].head(20)

    client = OpenAI(
        api_key=os.getenv("GEMINI_API_KEY"),
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    completion = client.beta.chat.completions.parse(
        model="gemini-2.5-flash", # Using a model optimized for Structured Outputs
        messages=[
            {
                "role": "system", 
                "content": "You are a data organizer. Analyze the list of lists provided by the user. Give each sub-list a short, descriptive name based on its contents."
            },
            {
                "role": "user", 
                "content": f"Here is the input data: {input_data} for the description use a maximum of {n_words} words."
            },
        ],
        response_format=OutputCollection, # Pass the Pydantic class here
    )

    parsed_response = completion.choices[0].message.parsed

    for group in parsed_response.groups:
        print(f"Group Name: {group.group_name}")
        print(f"Items: {group.items}")
        print("-" * 20)
    return parsed_response
test=get_gemini_labels("topic_info_2025.csv",n_words=3)