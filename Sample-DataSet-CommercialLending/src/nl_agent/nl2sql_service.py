"""
Natural Language to SQL Service using Vertex AI Gemini.
Converts user natural language queries into BigQuery SQL statements.
"""

import os
from typing import Dict, List
from src.core_tools.vertex_ai import VertexAI
from src.core_tools.bigquery_runner import BigQueryRunner


class NL2SQLService:
    """Service for converting natural language queries to SQL using Gemini LLM."""

    def __init__(self, project_id: str, location: str, dataset: str):
        self.project_id = project_id
        self.location = location
        self.dataset = dataset
        self.vertex_ai = VertexAI(project_id, location)
        self.bq_runner = BigQueryRunner(project_id, dataset)
        self.schema_context = self._load_schema_context()

    def _load_schema_context(self) -> str:
        """
        Load the target BigQuery schema as context for the LLM.
        Returns a formatted string describing all tables and columns.
        """
        schema_description = """
# BigQuery Schema for Commercial Lending Data Warehouse

## Dimension Tables:

### dim_borrower
- borrower_id (INT64): Unique borrower identifier
- borrower_name (STRING): Legal name of borrower
- borrower_type (STRING): Organization type (Corporation, LLC, Partnership)
- industry (STRING): Primary industry sector
- tax_id (STRING): Tax identification number
- country (STRING): Country code
- state (STRING): State/region
- city (STRING): City name
- postal_code (STRING): Postal code
- inception_date (DATE): Company inception date
- annual_revenue (NUMERIC): Annual revenue in USD
- employees (INT64): Number of employees

### dim_loan
- loan_id (INT64): Unique loan identifier
- borrower_id (INT64): Foreign key to dim_borrower
- facility_id (INT64): Foreign key to dim_facility
- index_id (INT64): Foreign key to dim_rate_index
- loan_number (STRING): Loan reference number
- status (STRING): Loan status (Active, Closed, Delinquent)
- origination_date (DATE): Loan origination date
- maturity_date (DATE): Loan maturity date
- principal_amount (NUMERIC): Original principal amount
- currency (STRING): Currency code (USD, EUR, GBP)
- purpose (STRING): Loan purpose (Acquisition, Refinance, Working Capital, Project Finance)
- loan_type (STRING): Type of loan (Term Loan, Revolver, Bridge, SBA, Equipment Financing)
- margin_bps (INT64): Margin in basis points
- amortization_type (STRING): Amortization type (Straight-Line, Interest-Only, Bullet)
- payment_frequency (STRING): Payment frequency (Monthly, Quarterly, Annually)
- compounding (STRING): Interest compounding method (Simple, Compound)
- index_name (STRING): Rate index name
- tenor_months (INT64): Rate index tenor in months
- index_currency (STRING): Rate index currency

### dim_facility
- facility_id (INT64): Unique facility identifier
- borrower_id (INT64): Foreign key to dim_borrower
- facility_type (STRING): Type of credit facility
- limit_amount (NUMERIC): Credit limit amount
- currency (STRING): Currency code
- origination_date (DATE): Facility origination date
- maturity_date (DATE): Facility maturity date
- interest_rate_floor_bps (INT64): Interest rate floor in basis points
- covenants_count (INT64): Number of covenants

### dim_rate_index
- index_id (INT64): Unique rate index identifier
- index_name (STRING): Rate index name (SOFR, LIBOR, EURIBOR)
- tenor_months (INT64): Tenor period in months
- index_currency (STRING): Currency of the index
- rate_type (STRING): Type of rate (Fixed, Floating)
- day_count_convention (STRING): Day count convention
- published_by (STRING): Publishing authority

### dim_collateral
- collateral_id (INT64): Unique collateral identifier
- loan_id (INT64): Foreign key to dim_loan
- collateral_type (STRING): Type of collateral (Real Estate, Equipment, Securities)
- value_amount (NUMERIC): Collateral value
- currency (STRING): Currency code
- valuation_date (DATE): Date of valuation
- lien_position (STRING): Lien position (First, Second, Third)
- location_country (STRING): Collateral location country
- location_state (STRING): Collateral location state

### dim_guarantor
- guarantor_id (INT64): Unique guarantor identifier
- borrower_id (INT64): Foreign key to dim_borrower
- guarantor_name (STRING): Guarantor name
- guarantor_type (STRING): Type of guarantor (Personal, Corporate)
- guarantee_type (STRING): Type of guarantee (Full, Limited, Partial)
- max_liability_amount (NUMERIC): Maximum liability amount
- currency (STRING): Currency code
- credit_score (INT64): Credit score
- ownership_pct (NUMERIC): Ownership percentage

### dim_risk_rating
- rating_id (INT64): Unique rating identifier
- loan_id (INT64): Foreign key to dim_loan
- borrower_id (INT64): Foreign key to dim_borrower
- rating_agency (STRING): Rating agency name
- rating_grade (STRING): Rating grade (AAA, AA, A, BBB, BB, B, CCC, CC, C, D)
- score (NUMERIC): Numeric risk score
- effective_date (DATE): Rating effective date
- expiry_date (DATE): Rating expiry date

### dim_syndicate_member
- member_id (INT64): Unique syndicate member identifier
- bank_name (STRING): Bank name
- role (STRING): Syndicate role (Lead Arranger, Co-Arranger, Participant)
- bank_rating (STRING): Bank credit rating
- country (STRING): Bank country

### dim_date
- date_key (INT64): Unique date identifier (YYYYMMDD format)
- date (DATE): Actual date
- year (INT64): Year
- quarter (INT64): Quarter (1-4)
- month (INT64): Month (1-12)
- day (INT64): Day of month

## Fact Tables:

### fact_payments
- payment_id (INT64): Unique payment identifier
- date_key (INT64): Foreign key to dim_date
- payment_date (DATE): Payment date
- loan_id (INT64): Foreign key to dim_loan
- borrower_id (INT64): Foreign key to dim_borrower
- facility_id (INT64): Foreign key to dim_facility
- index_id (INT64): Foreign key to dim_rate_index
- index_name (STRING): Rate index name
- tenor_months (INT64): Rate index tenor
- payment_amount (NUMERIC): Total payment amount
- principal_component (NUMERIC): Principal portion
- interest_component (NUMERIC): Interest portion
- fee_component (NUMERIC): Fee portion
- days_past_due (INT64): Days past due
- currency (STRING): Payment currency
- payment_method (STRING): Payment method (Wire, ACH, Check)
- margin_bps (INT64): Margin in basis points

### fact_loan_snapshot
- loan_id (INT64): Foreign key to dim_loan
- borrower_id (INT64): Foreign key to dim_borrower
- facility_id (INT64): Foreign key to dim_facility
- snapshot_date_key (INT64): Foreign key to dim_date
- snapshot_date (DATE): Snapshot date
- outstanding_principal (NUMERIC): Outstanding principal balance
- current_rate_pct (NUMERIC): Current interest rate percentage
- margin_bps (INT64): Margin in basis points
- rating_grade (STRING): Current risk rating grade
- score (NUMERIC): Current risk score

## Important Notes:
- All tables are in the `{project_id}.{dataset}` dataset
- Use fully qualified table names in queries: `{project_id}.{dataset}.table_name`
- Dates are in DATE format (YYYY-MM-DD)
- All monetary amounts are in NUMERIC type
- Foreign key relationships are maintained between dimensions and facts
        """
        return schema_description.format(
            project_id=self.project_id,
            dataset=self.dataset
        )

    async def convert_nl_to_sql(self, nl_query: str) -> Dict[str, str]:
        """
        Convert a natural language query to SQL using Vertex AI Gemini.

        Args:
            nl_query: Natural language query from the user

        Returns:
            Dictionary with 'sql' and 'explanation' keys
        """
        # Build the prompt for Gemini
        prompt = f"""You are an expert BigQuery SQL developer. Convert the following natural language query into a valid BigQuery SQL statement.

{self.schema_context}

## Task:
Convert this natural language query into BigQuery SQL:
"{nl_query}"

## Requirements:
1. Generate syntactically correct BigQuery SQL
2. Use fully qualified table names: `{self.project_id}.{self.dataset}.table_name`
3. Include appropriate JOINs when querying multiple tables
4. Use meaningful column aliases
5. Add LIMIT clause (max 1000 rows) for safety
6. Use aggregations (SUM, COUNT, AVG) when appropriate
7. Order results in a meaningful way

## Response Format:
Provide ONLY the SQL query without any explanations, markdown formatting, or additional text.
Just the raw SQL statement.

SQL:
"""

        try:
            # Call Vertex AI to generate SQL
            sql_response = self.vertex_ai.generate_text(prompt)

            # Clean up the response
            sql = sql_response.strip()

            # Remove any markdown code blocks if present
            if sql.startswith("```sql"):
                sql = sql.replace("```sql", "").replace("```", "").strip()
            elif sql.startswith("```"):
                sql = sql.replace("```", "").strip()

            # Generate explanation
            explanation = self._generate_explanation(nl_query, sql)

            return {
                "sql": sql,
                "explanation": explanation,
                "status": "success"
            }

        except Exception as e:
            print(f"NL2SQL Service: Error converting NL to SQL: {e}")
            return {
                "sql": "",
                "explanation": f"Error generating SQL: {str(e)}",
                "status": "error",
                "error": str(e)
            }

    def _generate_explanation(self, nl_query: str, sql: str) -> str:
        """Generate a human-readable explanation of the SQL query."""
        explanation = f"Converted your query '{nl_query}' into SQL. "

        # Add basic explanation based on SQL keywords
        if "SUM(" in sql.upper():
            explanation += "The query calculates totals. "
        if "COUNT(" in sql.upper():
            explanation += "The query counts records. "
        if "AVG(" in sql.upper():
            explanation += "The query calculates averages. "
        if "JOIN" in sql.upper():
            explanation += "The query combines data from multiple tables. "
        if "GROUP BY" in sql.upper():
            explanation += "Results are grouped for aggregation. "
        if "ORDER BY" in sql.upper():
            explanation += "Results are sorted. "

        return explanation

    def validate_sql(self, sql: str) -> Dict[str, any]:
        """
        Validate SQL syntax without executing it.

        Args:
            sql: SQL query to validate

        Returns:
            Dictionary with validation results
        """
        # Basic validation
        sql_upper = sql.upper()

        # Check for dangerous operations
        dangerous_keywords = ["DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE", "REPLACE"]
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                return {
                    "valid": False,
                    "error": f"Query contains dangerous keyword: {keyword}"
                }

        # Check for required SELECT
        if "SELECT" not in sql_upper:
            return {
                "valid": False,
                "error": "Query must be a SELECT statement"
            }

        # Check for project.dataset.table format
        if f"`{self.project_id}.{self.dataset}." not in sql:
            return {
                "valid": False,
                "error": f"Query must use fully qualified table names: `{self.project_id}.{self.dataset}.table_name`"
            }

        return {
            "valid": True,
            "message": "SQL query appears valid"
        }

    async def execute_query(self, sql: str, max_rows: int = 1000) -> Dict[str, any]:
        """
        Execute a SQL query against BigQuery.

        Args:
            sql: SQL query to execute
            max_rows: Maximum number of rows to return (default 1000)

        Returns:
            Dictionary with query results
        """
        # Validate SQL first
        validation = self.validate_sql(sql)
        if not validation["valid"]:
            return {
                "status": "error",
                "error": validation["error"],
                "columns": [],
                "rows": [],
                "row_count": 0
            }

        try:
            # Add LIMIT if not present
            if "LIMIT" not in sql.upper():
                sql = f"{sql.rstrip(';')} LIMIT {max_rows}"

            print(f"NL2SQL Service: Executing query:\n{sql}")

            # Execute query
            query_job = self.bq_runner.run_query(sql)

            # Get results
            results = list(query_job)

            # Extract column names
            columns = [field.name for field in query_job.schema]

            # Convert rows to list of lists
            rows = []
            for row in results:
                rows.append([row[col] for col in columns])

            return {
                "status": "success",
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "total_bytes_processed": query_job.total_bytes_processed if query_job.total_bytes_processed else 0
            }

        except Exception as e:
            print(f"NL2SQL Service: Error executing query: {e}")
            return {
                "status": "error",
                "error": str(e),
                "columns": [],
                "rows": [],
                "row_count": 0
            }

    async def interpret_results(self, nl_query: str, columns: List[str], rows: List[List], row_count: int) -> str:
        """
        Use LLM to interpret query results and provide a natural language answer.

        Args:
            nl_query: The original natural language question
            columns: Column names from the query result
            rows: Query result rows (limited for prompt)
            row_count: Total row count

        Returns:
            Natural language interpretation of the results
        """
        # Limit rows for the prompt
        sample_rows = rows[:20] if len(rows) > 20 else rows
        
        # Format results as a table string
        results_str = "Columns: " + ", ".join(columns) + "\n"
        for row in sample_rows:
            results_str += "  " + " | ".join(str(cell) if cell is not None else "NULL" for cell in row) + "\n"
        
        if row_count > 20:
            results_str += f"  ... and {row_count - 20} more rows\n"

        prompt = f"""You are a helpful data analyst assistant. A user asked a question about their commercial lending data, and a SQL query was executed. Analyze the results and provide a clear, concise answer to their question.

## User's Question:
"{nl_query}"

## Query Results ({row_count} rows returned):
{results_str}

## Instructions:
1. Directly answer the user's question based on the data
2. Highlight key insights or patterns if relevant
3. Use specific numbers and values from the results
4. Keep the response concise (2-4 sentences for simple queries, more for complex analysis)
5. Format numbers nicely (e.g., "$1,234,567" for money, "1.2M" for large numbers)
6. If the results are empty, explain what that means for their question

## Your Answer:
"""

        try:
            interpretation = self.vertex_ai.generate_text(prompt)
            return interpretation.strip()
        except Exception as e:
            print(f"NL2SQL Service: Error interpreting results: {e}")
            return f"Query returned {row_count} rows. Unable to generate natural language interpretation."

    async def query_and_interpret(self, nl_query: str, max_rows: int = 1000) -> Dict[str, any]:
        """
        Full pipeline: Convert NL to SQL, execute, and interpret results.

        Args:
            nl_query: Natural language question from the user
            max_rows: Maximum rows to return

        Returns:
            Dictionary with sql, results, and natural language interpretation
        """
        # Step 1: Convert NL to SQL
        nl2sql_result = await self.convert_nl_to_sql(nl_query)
        
        if nl2sql_result.get("status") == "error":
            return {
                "status": "error",
                "error": nl2sql_result.get("error", "Failed to convert query"),
                "sql": "",
                "interpretation": "",
                "columns": [],
                "rows": [],
                "row_count": 0
            }
        
        sql = nl2sql_result.get("sql", "")
        
        # Step 2: Execute the query
        exec_result = await self.execute_query(sql, max_rows)
        
        if exec_result.get("status") == "error":
            return {
                "status": "error",
                "error": exec_result.get("error", "Query execution failed"),
                "sql": sql,
                "interpretation": "",
                "columns": [],
                "rows": [],
                "row_count": 0
            }
        
        # Step 3: Interpret the results
        interpretation = await self.interpret_results(
            nl_query,
            exec_result.get("columns", []),
            exec_result.get("rows", []),
            exec_result.get("row_count", 0)
        )
        
        return {
            "status": "success",
            "sql": sql,
            "explanation": nl2sql_result.get("explanation", ""),
            "interpretation": interpretation,
            "columns": exec_result.get("columns", []),
            "rows": exec_result.get("rows", []),
            "row_count": exec_result.get("row_count", 0),
            "total_bytes_processed": exec_result.get("total_bytes_processed", 0)
        }
