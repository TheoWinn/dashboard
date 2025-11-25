import os
from pydantic import BaseModel
from typing import List
from openai import OpenAI


class NamedGroup(BaseModel):
    group_name: str       
    items: List[str]     

class OutputCollection(BaseModel):
    groups: List[NamedGroup]

input_data = [
    ["apple", "banana", "cherry"],
    ["garbage truck", "landfill", "recycling bin"],
    ["joyful reunion", "tears of happiness", "hug"]
]

n_words = 1 
client = OpenAI(
    api_key="AIzaSyBTQ7JeGf9rsyxkflPh2_Bxb1aRcUe4Ay0",
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