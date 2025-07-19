# Claude Desktop MCP Server Setup Guide

## ✅ Configuration Complete

Your M&A Research Assistant MCP server has been successfully configured in Claude Desktop!

## 🔄 Next Steps

### 1. Restart Claude Desktop
- **Completely quit** Claude Desktop (Cmd+Q)
- **Restart** Claude Desktop
- The MCP server will automatically connect

### 2. Verify Connection
In Claude Desktop, you should see:
- 🔧 MCP tools icon in the interface
- Server name: **"ma-research-assistant"**
- **19 available tools** for M&A research

### 3. Available MCP Tools

#### Core Analysis Tools
- `analyze_company` - Complete company analysis pipeline
- `scrape_website` - Intelligent website scraping
- `get_linkedin_data` - LinkedIn company data extraction
- `score_dimension` - Individual scoring evaluation
- `enrich_company_data` - Data enhancement from multiple sources

#### Lead Management Tools  
- `qualify_lead` - Multi-tier lead qualification
- `generate_investment_thesis` - AI-powered investment analysis
- `manage_lead_nurturing` - Lead tier and activity management
- `override_company_tier` - Manual tier overrides

#### Search & History Tools
- `get_company_history` - Historical analysis retrieval
- `compare_analyses` - Compare multiple analyses
- `search_companies` - Search analyzed companies

#### Bulk Operations
- `bulk_analyze` - Parallel multi-company analysis
- `bulk_filter` - Filter companies by criteria
- `run_custom_scoring` - Execute custom scoring systems

#### Export & Reporting
- `export_report` - Multi-format report generation
- `generate_xlsx_export` - Professional Excel exports

#### Management Tools
- `manage_scoring_systems` - Custom scoring system management
- `manage_company_lists` - Active/future list management
- `update_metadata` - Manual metadata updates

## 🏢 Test Companies

Try analyzing these sample companies:

### Jonas Fitness
```
Company: Jonas Fitness
Website: https://jonasfitness.com
Focus: Fitness management software
```

### ClubWise  
```
Company: ClubWise
Website: https://clubwise.com
Focus: UK-based club management platform
```

### RunSignUp
```
Company: RunSignUp
Website: https://runsignup.com
Focus: Race registration and event management
```

## 💡 Example Usage

### Basic Company Analysis
"Please analyze Jonas Fitness as a potential acquisition target using the analyze_company tool."

### Bulk Analysis
"Can you analyze multiple fitness software companies: Jonas Fitness, ClubWise, and RunSignUp using bulk_analyze?"

### Investment Thesis
"Generate an investment thesis for Jonas Fitness after analyzing the company."

### Excel Report
"Create a professional Excel report comparing the analysis results for all three companies."

## 🔧 Troubleshooting

### If MCP Tools Don't Appear:
1. Check that Claude Desktop is completely restarted
2. Verify the server starts: `./start_mcp_server.sh`
3. Check logs in Claude Desktop developer console

### If Analysis Fails:
1. Ensure AWS credentials are valid in `.env`
2. Check S3 bucket permissions
3. Verify Apify API token is active

### Configuration Location
```
/Users/jamespeltier/Library/Application Support/Claude/claude_desktop_config.json
```

## 📊 Server Capabilities

- **8-Dimension Scoring**: VMS focus, revenue model, pricing, etc.
- **Geographic Filtering**: North America (all verticals), UK (sports/fitness only)
- **Lead Qualification**: Q1-Q5 assessment framework
- **AI-Powered Analysis**: Claude 3.5 Sonnet with Nova Pro fallback
- **Professional Reports**: Excel with formatting, charts, multiple sheets
- **S3 Storage**: Versioned analysis storage with structured organization

Your M&A Research Assistant is ready for comprehensive company analysis! 🚀