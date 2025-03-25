# SQLGenius - AI-Powered SQL Assistant

SQLGenius is an intelligent SQL assistant that helps you query your BigQuery database using natural language. Built with MCP (Model Context Protocol), Vertex AI's Gemini Pro, and Streamlit.

## 🌟 Features

- Natural language to SQL conversion using Gemini Pro
- Interactive Streamlit UI with multiple tabs
- Real-time query execution and visualization
- Database schema explorer
- Query history tracking
- Safe query validation
- BigQuery integration
- MCP-based architecture

## 🚀 Installation

1. Clone the repository and navigate to the project directory:
```bash
cd sql_mcp_server
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy the `.env.example` file to `.env` and fill in your configuration:
```bash
cp .env.example .env
```

4. Set up your environment variables in `.env`:
```
PROJECT_ID=your-project-id
DATASET_ID=your-dataset-id
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account.json
VERTEX_AI_LOCATION=us-central1
```

## 🎮 Usage

1. Start the application:
```bash
streamlit run streamlit_app.py
```

2. The MCP server will start automatically when the Streamlit app launches

3. Use the tabs to:
   - Ask natural language questions about your data
   - Write SQL queries directly
   - Explore your database schema

## 📊 Interface Tabs

### 💬 Natural Language Query
Ask questions in plain English and get SQL results:
- "Show me the top 5 customers by revenue"
- "What products have the highest sales in January?"
- "How many orders were placed last month?"

### 📊 SQL Query
Write and execute SQL queries directly:
```sql
SELECT * FROM orders 
WHERE order_date > '2023-01-01' 
ORDER BY total_amount DESC
LIMIT 10
```

### 📋 Database Explorer
- Browse available tables
- View table schemas
- See sample data from any table

## 🔒 Security Features

- Only SELECT queries are permitted
- Query validation to prevent dangerous operations
- Secure credential management
- Error handling and input validation

## 🛠️ Architecture

SQLGenius uses the Model Context Protocol (MCP) to expose tools that enable:

1. **Natural Language Processing**: Convert English questions to SQL
2. **Data Exploration**: Fetch schema information and sample data
3. **SQL Execution**: Run validated queries against your database

The architecture consists of:
- **MCP Server**: Handles DB connection and provides tools
- **Streamlit Frontend**: User interface for interacting with the system
- **Vertex AI (Gemini Pro)**: Powers natural language understanding
- **BigQuery**: Executes SQL queries on your data

## 📝 MCP Tools

The following MCP tools are available:

1. `execute_nl_query`: Execute a natural language query
2. `execute_sql_query`: Execute a raw SQL query
3. `list_tables`: List all available tables
4. `get_table_schema`: Get schema for a specific table

## 📚 Advanced Usage

To add custom tools to the MCP server:

1. Edit the `register_tools()` method in `sql_mcp_server.py`
2. Add your custom tool using the `@self.tool()` decorator
3. Restart the server

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
