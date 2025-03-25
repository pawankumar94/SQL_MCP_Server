import os
import json
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from google.cloud import bigquery
from sqlalchemy import create_engine
from langchain.sql_database import SQLDatabase
from langchain_google_vertexai import VertexAI
from mcp.server.fastmcp import FastMCP
from mcp import Tool, Resource

# Load environment variables
load_dotenv()

class SQLGeniusServer(FastMCP):
    def __init__(self):
        """Initialize the SQL MCP server with tools and resources"""
        super().__init__("SQLGenius")
        
        # Load configuration from environment variables
        self.project_id = os.getenv("PROJECT_ID")
        self.dataset_id = os.getenv("DATASET_ID")
        self.location = os.getenv("VERTEX_AI_LOCATION", "us-central1")
        
        # Initialize database and LLM
        self.setup_database()
        self.setup_llm()
        
        # Register tools
        self.register_tools()
        
    def setup_database(self):
        """Initialize BigQuery database connection"""
        try:
            self.client = bigquery.Client()
            sqlalchemy_url = f"bigquery://{self.project_id}/{self.dataset_id}"
            self.engine = create_engine(sqlalchemy_url)
            self.db = SQLDatabase(self.engine)
            print(f"✅ Connected to BigQuery: {self.project_id}.{self.dataset_id}")
        except Exception as e:
            print(f"❌ Database connection error: {str(e)}")
            raise Exception(f"Failed to initialize database: {str(e)}")

    def setup_llm(self):
        """Initialize Vertex AI LLM"""
        try:
            self.llm = VertexAI(
                model_name="gemini-1.0-pro",
                max_output_tokens=2048,
                temperature=0.3,
                top_p=0.8,
                top_k=40,
                project=self.project_id,
                location=self.location
            )
            print(f"✅ Connected to Vertex AI in {self.location}")
        except Exception as e:
            print(f"❌ LLM initialization error: {str(e)}")
            raise Exception(f"Failed to initialize LLM: {str(e)}")

    def register_tools(self):
        """Register all MCP tools and resources"""
        
        # Tool for executing natural language queries
        @self.tool("execute_nl_query", "Execute a natural language query on the SQL database")
        async def execute_nl_query(query: str) -> Dict[str, Any]:
            """
            Execute a natural language query on the SQL database
            
            Args:
                query: The natural language query to execute
                
            Returns:
                A dictionary with the generated SQL, results, and explanation
            """
            # Get context about available tables
            tables = self.get_available_tables()
            context = f"Available tables: {', '.join(tables)}. "
            
            # Generate SQL response using LLM
            prompt = f"{context}\nUser query: {query}\nGenerate and execute an appropriate SQL query."
            
            # Invoke LLM
            llm_response = self.llm.invoke(prompt)
            
            # Extract SQL query from LLM response
            sql_query = self._extract_sql_query(llm_response)
            
            if not sql_query:
                return {
                    "error": "Could not generate valid SQL query",
                    "explanation": llm_response
                }
            
            # Validate query for safety
            if not self.validate_query(sql_query):
                return {
                    "error": "Only SELECT queries are allowed",
                    "explanation": "For security reasons, only SELECT queries are permitted."
                }
                
            # Execute query
            try:
                result = self.db.run(sql_query)
                
                return {
                    "query": sql_query,
                    "result": result,
                    "explanation": llm_response
                }
            except Exception as e:
                return {
                    "error": f"Error executing query: {str(e)}",
                    "query": sql_query,
                    "explanation": llm_response
                }
        
        # Tool for executing raw SQL queries
        @self.tool("execute_sql_query", "Execute a SQL query directly on the database")
        async def execute_sql_query(query: str) -> Dict[str, Any]:
            """
            Execute a SQL query directly on the database
            
            Args:
                query: The SQL query to execute
                
            Returns:
                A dictionary with the results and status
            """
            # Validate query for safety
            if not self.validate_query(query):
                return {
                    "error": "Only SELECT queries are allowed",
                    "explanation": "For security reasons, only SELECT queries are permitted."
                }
                
            # Execute query
            try:
                result = self.db.run(query)
                
                return {
                    "query": query,
                    "result": result,
                    "success": True
                }
            except Exception as e:
                return {
                    "error": f"Error executing query: {str(e)}",
                    "query": query,
                    "success": False
                }
        
        # Tool for listing available tables
        @self.tool("list_tables", "List all available tables in the dataset")
        async def list_tables() -> Dict[str, Any]:
            """
            List all available tables in the dataset
            
            Returns:
                A dictionary with the list of tables
            """
            try:
                tables = self.get_available_tables()
                return {
                    "tables": tables,
                    "project_id": self.project_id,
                    "dataset_id": self.dataset_id,
                    "count": len(tables)
                }
            except Exception as e:
                return {
                    "error": f"Error listing tables: {str(e)}"
                }
        
        # Tool for getting table schema
        @self.tool("get_table_schema", "Get the schema for a specific table")
        async def get_table_schema(table_name: str) -> Dict[str, Any]:
            """
            Get the schema for a specific table
            
            Args:
                table_name: The name of the table to get schema for
                
            Returns:
                A dictionary with the table schema
            """
            try:
                table_ref = self.client.dataset(self.dataset_id).table(table_name)
                table = self.client.get_table(table_ref)
                
                # Format schema in a more readable way
                schema = []
                for field in table.schema:
                    schema.append({
                        "name": field.name,
                        "type": field.field_type,
                        "description": field.description
                    })
                
                return {
                    "table_name": table_name,
                    "schema": schema,
                    "num_rows": table.num_rows,
                    "size_bytes": table.num_bytes
                }
            except Exception as e:
                return {
                    "error": f"Error getting schema for table {table_name}: {str(e)}"
                }

    def get_available_tables(self) -> List[str]:
        """Get list of available tables in the dataset"""
        tables = self.client.list_tables(f"{self.project_id}.{self.dataset_id}")
        return [table.table_id for table in tables]

    def validate_query(self, query: str) -> bool:
        """Validate if the query is safe to execute"""
        dangerous_keywords = ["insert", "update", "delete", "drop", "alter", "create"]
        return not any(keyword in query.lower() for keyword in dangerous_keywords)

    def _extract_sql_query(self, llm_response: str) -> Optional[str]:
        """Extract SQL query from LLM response"""
        try:
            # Look for SQL query between backticks or SQL keywords
            if "```sql" in llm_response:
                query = llm_response.split("```sql")[1].split("```")[0].strip()
            elif "```" in llm_response and "SELECT" in llm_response.upper():
                code_blocks = llm_response.split("```")
                for i in range(1, len(code_blocks), 2):
                    if "SELECT" in code_blocks[i].upper():
                        query = code_blocks[i].strip()
                        if query.startswith("sql"):
                            query = query[3:].strip()
                        return query
            elif "SELECT" in llm_response.upper():
                query = llm_response[llm_response.upper().find("SELECT"):]
                # Try to find where the query ends (next paragraph or end of text)
                end_positions = [pos for pos in [
                    query.find("\n\n"), 
                    query.find("\r\n\r\n"),
                    query.find(". "),
                    query.find(".\n")
                ] if pos != -1]
                
                if end_positions:
                    query = query[:min(end_positions)]
                
                return query.strip()
            else:
                return None
            return query
        except Exception as e:
            print(f"Error extracting SQL query: {str(e)}")
            return None

# Create an instance of the server globally for MCP to find
server = SQLGeniusServer()

if __name__ == "__main__":
    print("Starting SQLGenius MCP Server...")
    print(f"Server registered tools successfully")
    print("Starting server...")
    server.run() 