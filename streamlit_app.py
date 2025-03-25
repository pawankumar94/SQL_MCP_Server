import os
import json
import asyncio
import streamlit as st
import pandas as pd
import psutil
import subprocess
import time
import traceback
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MCP server path - fixed to use correct path
MCP_SERVER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sql_mcp_server.py")

# Set page config
st.set_page_config(
    page_title="SQLGenius - Intelligent SQL Assistant",
    page_icon="🔍",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
    }
    .output-container {
        background-color: #f0f2f6;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .sql-box {
        background-color: #f8f9fa;
        border-left: 3px solid #4CAF50;
        padding: 10px;
        margin: 10px 0;
        font-family: monospace;
    }
    .results-box {
        border: 1px solid #e6e9ef;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
        overflow-x: auto;
    }
    .success-box {
        background-color: #f0fff4;
        border: 1px solid #9ae6b4;
        border-radius: 5px;
        padding: 10px;
        margin-bottom: 10px;
    }
    .error-box {
        background-color: #fff5f5;
        border: 1px solid #feb2b2;
        border-radius: 5px;
        padding: 10px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Check if a process is running based on a command pattern
def is_process_running(pattern):
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline', [])
            if cmdline and any(pattern in cmd for cmd in cmdline if cmd):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

# Function to start the MCP server
def start_mcp_server():
    if is_process_running("sql_mcp_server.py"):
        st.sidebar.success("🟢 MCP server is already running!")
        return True
    
    try:
        cmd = ["python", MCP_SERVER_PATH]
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )
        
        # Give the server some time to start
        time.sleep(2)
        
        # Check if the process is still running (didn't crash immediately)
        if process.poll() is None:
            st.sidebar.success("🟢 MCP server started successfully!")
            return True
        else:
            stdout, stderr = process.communicate()
            st.sidebar.error(f"🔴 MCP server failed to start: {stderr}")
            return False
    except Exception as e:
        st.sidebar.error(f"🔴 Error starting MCP server: {str(e)}")
        return False

# Function to get available tools from the MCP server
async def get_tools():
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        
        # Create server parameters for stdio connection
        server_params = StdioServerParameters(
            command="python",  # Executable
            args=[MCP_SERVER_PATH],  # Path to the MCP server script
            env=None  # Use current environment
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the connection
                await session.initialize()
                
                # List available tools
                tools_result = await session.list_tools()
                
                # Extract tools from the result
                if hasattr(tools_result, 'tools'):
                    return tools_result.tools
                else:
                    st.sidebar.warning("Unexpected tools result format")
                    return []
    except Exception as e:
        st.sidebar.error(f"Error getting tools: {str(e)}")
        return []

# Function to call an MCP tool
async def call_tool(tool_name, params):
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        
        # Create server parameters for stdio connection
        server_params = StdioServerParameters(
            command="python",  # Executable
            args=[MCP_SERVER_PATH],  # Path to the MCP server script
            env=None  # Use current environment
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the connection
                await session.initialize()
                
                # Call the tool
                result = await session.call_tool(tool_name, arguments=params)
                
                # Extract content from the result
                if hasattr(result, 'content') and result.content:
                    content_item = result.content[0]
                    if hasattr(content_item, 'text'):
                        return json.loads(content_item.text)
                    elif hasattr(content_item, 'json'):
                        return content_item.json
                
                return str(result)
    except Exception as e:
        traceback.print_exc()
        st.error(f"Error calling tool: {str(e)}")
        return {"error": f"Error: {str(e)}"}

# Initialize session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'server_started' not in st.session_state:
    st.session_state.server_started = False
if 'tools' not in st.session_state:
    st.session_state.tools = []

# Title and description
st.title("🔍 SQLGenius")
st.markdown("""
Welcome to SQLGenius - Your AI-powered SQL Assistant! 
Ask questions about your data in plain English, and I'll help you query it effectively.
""")

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Start MCP server on app startup if it's not already running
    if not st.session_state.server_started:
        st.session_state.server_started = start_mcp_server()
    
    # Display server status
    server_status = "🟢 Connected" if is_process_running("sql_mcp_server.py") else "🔴 Disconnected"
    st.markdown(f"**Server Status:** {server_status}")
    
    # Button to restart the server
    if st.button("🔄 Restart Server"):
        st.session_state.server_started = start_mcp_server()
    
    # Get available tools
    if st.session_state.server_started and not st.session_state.tools:
        try:
            # Get tools using the async function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            st.session_state.tools = loop.run_until_complete(get_tools())
            loop.close()
        except Exception as e:
            st.sidebar.error(f"Failed to get tools: {str(e)}")
    
    # Show tools
    st.subheader("🛠️ Available Tools")
    if st.session_state.tools:
        for tool in st.session_state.tools:
            st.markdown(f"**{tool.name}**: {tool.description}")
    else:
        st.warning("No tools found. Server may not be properly connected.")
        
        # Refresh tools button
        if st.button("🔄 Refresh Tools"):
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                st.session_state.tools = loop.run_until_complete(get_tools())
                loop.close()
            except Exception as e:
                st.sidebar.error(f"Failed to refresh tools: {str(e)}")

# Create tabs for different functionalities
tab1, tab2, tab3 = st.tabs(["💬 Natural Language Query", "📊 SQL Query", "📋 Database Explorer"])

# Tab 1: Natural Language Query
with tab1:
    st.header("Ask Questions in Natural Language")
    st.markdown("Ask questions about your data in plain English, and SQLGenius will generate and execute appropriate SQL queries.")
    
    nl_query = st.text_area("💭 Ask your question:", height=100, 
                          placeholder="Example: 'Show me the top 5 products by revenue'")
    
    if st.button("🚀 Execute Query", key="nl_execute"):
        if not nl_query:
            st.warning("⚠️ Please enter a question first!")
        else:
            with st.spinner("🔄 Processing your question..."):
                try:
                    # Call execute_nl_query tool
                    result = asyncio.run(call_tool("execute_nl_query", {"query": nl_query}))
                    
                    if "error" in result:
                        st.error(f"❌ Error: {result['error']}")
                        if "explanation" in result:
                            st.info(f"Explanation: {result['explanation']}")
                    else:
                        # Add to chat history
                        st.session_state.chat_history.append({
                            "query": nl_query,
                            "response": result
                        })
                        
                        # Display results
                        st.success("✅ Query executed successfully!")
                        
                        st.subheader("Generated SQL Query")
                        st.code(result["query"], language="sql")
                        
                        st.subheader("Explanation")
                        st.write(result["explanation"])
                        
                        st.subheader("Results")
                        # Try to convert string results to DataFrame if it's a list/dict
                        try:
                            if isinstance(result["result"], (str, list, dict)):
                                if isinstance(result["result"], str):
                                    try:
                                        # Try to parse as JSON
                                        data = json.loads(result["result"])
                                        df = pd.DataFrame(data)
                                        st.dataframe(df)
                                    except:
                                        st.write(result["result"])
                                else:
                                    df = pd.DataFrame(result["result"])
                                    st.dataframe(df)
                            else:
                                st.write(result["result"])
                        except:
                            st.write(result["result"])
                        
                except Exception as e:
                    st.error(f"❌ Error executing query: {str(e)}")
                    st.code(traceback.format_exc(), language="python")

# Tab 2: SQL Query
with tab2:
    st.header("Write SQL Queries Directly")
    st.markdown("Execute SQL queries directly against your database.")
    
    sql_query = st.text_area("📝 Enter your SQL query:", height=150,
                           placeholder="Example: SELECT * FROM products LIMIT 10")
    
    if st.button("🚀 Execute SQL", key="sql_execute"):
        if not sql_query:
            st.warning("⚠️ Please enter a SQL query first!")
        else:
            with st.spinner("🔄 Executing SQL query..."):
                try:
                    # Call execute_sql_query tool
                    result = asyncio.run(call_tool("execute_sql_query", {"query": sql_query}))
                    
                    if "error" in result:
                        st.error(f"❌ Error: {result['error']}")
                    else:
                        # Display results
                        st.success("✅ Query executed successfully!")
                        
                        st.subheader("Results")
                        # Try to convert string results to DataFrame if it's a list/dict
                        try:
                            if isinstance(result["result"], (str, list, dict)):
                                if isinstance(result["result"], str):
                                    try:
                                        # Try to parse as JSON
                                        data = json.loads(result["result"])
                                        df = pd.DataFrame(data)
                                        st.dataframe(df)
                                    except:
                                        st.write(result["result"])
                                else:
                                    df = pd.DataFrame(result["result"])
                                    st.dataframe(df)
                            else:
                                st.write(result["result"])
                        except:
                            st.write(result["result"])
                        
                except Exception as e:
                    st.error(f"❌ Error executing SQL: {str(e)}")

# Tab 3: Database Explorer
with tab3:
    st.header("Explore Your Database")
    st.markdown("Browse tables and schemas in your database.")
    
    if st.button("🔄 Refresh Tables", key="refresh_tables"):
        with st.spinner("Fetching tables..."):
            try:
                # Call list_tables tool
                result = asyncio.run(call_tool("list_tables", {}))
                
                if "error" in result:
                    st.error(f"❌ Error: {result['error']}")
                else:
                    st.session_state.tables_info = result
            except Exception as e:
                st.error(f"❌ Error fetching tables: {str(e)}")
    
    # Display tables if available
    if 'tables_info' in st.session_state:
        st.subheader(f"Tables in {st.session_state.tables_info['project_id']}.{st.session_state.tables_info['dataset_id']}")
        st.write(f"Found {st.session_state.tables_info['count']} tables:")
        
        # Create a grid of buttons for tables
        cols = st.columns(3)
        for i, table in enumerate(st.session_state.tables_info['tables']):
            with cols[i % 3]:
                if st.button(f"📊 {table}", key=f"table_{table}"):
                    with st.spinner(f"Fetching schema for {table}..."):
                        try:
                            # Call get_table_schema tool
                            result = asyncio.run(call_tool("get_table_schema", {"table_name": table}))
                            
                            if "error" in result:
                                st.error(f"❌ Error: {result['error']}")
                            else:
                                st.session_state.selected_table = result
                        except Exception as e:
                            st.error(f"❌ Error fetching schema: {str(e)}")
    else:
        st.info("Click 'Refresh Tables' to see the available tables.")
    
    # Display selected table schema if available
    if 'selected_table' in st.session_state:
        st.subheader(f"Schema for {st.session_state.selected_table['table_name']}")
        
        # Table info
        st.write(f"**Rows:** {st.session_state.selected_table['num_rows']:,}")
        st.write(f"**Size:** {st.session_state.selected_table['size_bytes']/1024/1024:.2f} MB")
        
        # Create DataFrame from schema
        schema_df = pd.DataFrame(st.session_state.selected_table['schema'])
        st.dataframe(schema_df, use_container_width=True)
        
        # Sample data button
        if st.button(f"👁️ Preview {st.session_state.selected_table['table_name']}", key="preview_table"):
            with st.spinner(f"Fetching sample data..."):
                try:
                    # Execute a sample query
                    sample_query = f"SELECT * FROM `{st.session_state.selected_table['table_name']}` LIMIT 10"
                    result = asyncio.run(call_tool("execute_sql_query", {"query": sample_query}))
                    
                    if "error" in result:
                        st.error(f"❌ Error: {result['error']}")
                    else:
                        st.subheader(f"Sample data from {st.session_state.selected_table['table_name']}")
                        
                        # Display as DataFrame
                        try:
                            df = pd.DataFrame(result["result"])
                            st.dataframe(df, use_container_width=True)
                        except:
                            st.write(result["result"])
                except Exception as e:
                    st.error(f"❌ Error fetching sample data: {str(e)}")

# Display chat history at the bottom
if st.session_state.chat_history:
    st.subheader("📜 Query History")
    for i, chat in enumerate(reversed(st.session_state.chat_history)):
        with st.expander(f"Query {len(st.session_state.chat_history) - i}"):
            st.markdown("**Question:**")
            st.write(chat["query"])
            
            if "query" in chat["response"]:
                st.markdown("**SQL Query:**")
                st.code(chat["response"]["query"], language="sql")
            
            if "result" in chat["response"]:
                st.markdown("**Results:**")
                # Try to display as DataFrame if possible
                try:
                    df = pd.DataFrame(chat["response"]["result"])
                    st.dataframe(df)
                except:
                    st.write(chat["response"]["result"]) 