import os
import random
import pytz
from datetime import datetime
import dotenv
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
import streamlit as st
from langchain import agents
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool
from langchain_openai import AzureChatOpenAI
from langchain.agents import create_react_agent
from langchain_core.tools import tool
from langchain_community.callbacks.streamlit import (
    StreamlitCallbackHandler,
)

dotenv.load_dotenv()

st.set_page_config(
    page_title="AI bot that can use tools"
)
st.title("💬 AI bot that can use tools")
st.caption("🚀 A Bot that can use tools to answer questions about time and space")

def get_session_id() -> str:
    id = random.randint(0, 1000000)
    return "00000000-0000-0000-0000-" + str(id).zfill(12)

if "session_id" not in st.session_state:
    st.session_state["session_id"] = get_session_id()
    print("started new session: " + st.session_state["session_id"])
    st.write("You are running in session: " + st.session_state["session_id"])

llm: AzureChatOpenAI = None

from openai import DefaultHttpxClient
import httpx
http_client=DefaultHttpxClient()
ahttp_client=httpx.AsyncClient()

if "AZURE_OPENAI_API_KEY" in os.environ:

    # it seems codespaces messes with the proxy settings
    if "CODESPACES" in os.environ:
        llm = AzureChatOpenAI(
            http_client=http_client,
            http_async_client=ahttp_client,
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_deployment=os.getenv("AZURE_OPENAI_COMPLETION_DEPLOYMENT_NAME"),
            openai_api_version=os.getenv("AZURE_OPENAI_VERSION"),
            temperature=0,
            streaming=True
        )
    else:
        llm = AzureChatOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_deployment=os.getenv("AZURE_OPENAI_COMPLETION_DEPLOYMENT_NAME"),
            openai_api_version=os.getenv("AZURE_OPENAI_VERSION"),
            temperature=0,
            streaming=True
        )
else:
    token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
    llm = AzureChatOpenAI(
        http_client=http_client,
        http_async_client=ahttp_client,
        azure_ad_token_provider=token_provider,
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        azure_deployment=os.getenv("AZURE_OPENAI_COMPLETION_DEPLOYMENT_NAME"),
        openai_api_version=os.getenv("AZURE_OPENAI_VERSION"),
        temperature=0,
        openai_api_type="azure_ad",
        streaming=True
    )
    
@tool
def get_current_time(location: str) -> str:
    "Get the current time in the given location. The pytz is used to get the timezone for that location. Location names should be in a format like America/Seattle, Asia/Bangkok, Europe/London. Anything in Germany should be Europe/Berlin"
    try:
        print("get current time for location: ", location)
        location = str.replace(location, " ", "")
        location = str.replace(location, "\"", "")
        location = str.replace(location, "\n", "")
        # Get the timezone for the city
        timezone = pytz.timezone(location)

        # Get the current time in the timezone
        now = datetime.now(timezone)
        current_time = now.strftime("%I:%M:%S %p")

        return current_time
    except Exception as e:
        print("Error: ", e)
        return "Sorry, I couldn't find the timezone for that location."
    
tools = []
# tools = [get_current_time]
# tools = [get_current_username, get_current_location, get_current_time]

commandprompt = '''
    ##
    You are a helpfull assistent and should respond to user questions.
    If you cannot answer a question then say so explicitly and stop.
    
    '''

promptString = commandprompt +  """Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer

Thought: you should always think about what to do

Action: the action to take, should be one of [{tool_names}] or no action at all. Make sure that Actions are not commands. They should be the name of the tool to use.

Action Input: the input to the action according to the tool signature, if a tool should be used.

Observation: the result of the action

... (this Thought/Action/Action Input/Observation can repeat N times)

Thought: There are no tools to be used or I now know the final answer.

Final Answer: the final answer to the original input question

Begin!

Question: {input}

Thought:{agent_scratchpad}

"""
prompt = PromptTemplate.from_template(promptString)

agent = create_react_agent(llm, tools, prompt)

agent_executor = agents.AgentExecutor(
        name="Tools Agent",
        agent=agent, tools=tools,  verbose=True, handle_parsing_errors=True, max_iterations=10, return_intermediate_steps=True,
    )

if prompt := st.chat_input():

    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        st_callback = StreamlitCallbackHandler(st.container())
        response = agent_executor.invoke(
            {"input": prompt}, {"callbacks": [st_callback]}
        )
        st.write(response["output"])
