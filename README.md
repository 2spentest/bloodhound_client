# BloodHound CE Custom Query Importer

A Python script for importing custom Cypher queries into BloodHound Community Edition (CE). This tool allows you to easily import queries from various sources including GitHub repositories, local files, and direct JSON URLs.

## Features

- Import custom queries from multiple sources:
  - GitHub repositories
  - Local files (JSON, YAML, plain text)
  - Direct JSON URLs
- Support for various query formats:
  - Compass/ZephrFish format
  - Simple array format
  - Plain text queries
- Built-in rate limiting to prevent API throttling
- Automatic retry mechanism for failed requests
- Detailed error reporting and import summaries

## Prerequisites

- Python 3.6 or higher
- BloodHound CE instance
- BloodHound API credentials (Token ID and Token Key)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/bloodhound-query-importer.git
cd bloodhound-query-importer
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
python bloodhound_client.py --token-id "YOUR_TOKEN_ID" --token-key "YOUR_TOKEN_KEY" --url "YOUR_BLOODHOUND_URL"
```

### Import from JSON URL

```bash
python bloodhound_client.py --token-id "YOUR_TOKEN_ID" --token-key "YOUR_TOKEN_KEY" --url "YOUR_BLOODHOUND_URL" --json-url "https://raw.githubusercontent.com/CompassSecurity/bloodhoundce-resources/main/customqueries.json"
```

### Import from GitHub Repository

```bash
python bloodhound_client.py --token-id "YOUR_TOKEN_ID" --token-key "YOUR_TOKEN_KEY" --url "YOUR_BLOODHOUND_URL" --github "https://github.com/CompassSecurity/bloodhoundce-resources" --branch "main" --path "customqueries"
```

### Import from Local File

```bash
python bloodhound_client.py --token-id "YOUR_TOKEN_ID" --token-key "YOUR_TOKEN_KEY" --url "YOUR_BLOODHOUND_URL" --file "path/to/your/queries.json"
```

### Rate Limiting

To adjust the delay between requests (default: 0.5 seconds):

```bash
python bloodhound_client.py --token-id "YOUR_TOKEN_ID" --token-key "YOUR_TOKEN_KEY" --url "YOUR_BLOODHOUND_URL" --rate-limit 1.0
```

## Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--url` | BloodHound instance URL | http://localhost:8080 |
| `--token-id` | BloodHound API token ID | (required) |
| `--token-key` | BloodHound API token key | (required) |
| `--json-url` | URL to JSON file containing queries | |
| `--github` | GitHub repository URL | |
| `--file` | Local file path | |
| `--branch` | GitHub branch name | main |
| `--path` | Path within repository or directory | |
| `--rate-limit` | Delay between requests in seconds | 0.5 |

## Supported Query Formats

### Compass/ZephrFish Format
```json
{
  "queries": [
    {
      "name": "Query Group Name",
      "category": "Category Name",
      "queryList": [
        {
          "final": true,
          "query": "MATCH (n) RETURN n"
        }
      ]
    }
  ]
}
```

### Simple Array Format
```json
[
  {
    "name": "Query Name",
    "query": "MATCH (n) RETURN n",
    "description": "Query Description"
  }
]
```

## Error Handling

The script includes comprehensive error handling:
- Rate limit detection and automatic retry
- Detailed error messages for failed imports
- Progress reporting during import
- Summary of successful and failed imports

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [BloodHound CE](https://github.com/BloodHoundAD/BloodHound)
- [Compass Security BloodHound CE Resources](https://github.com/CompassSecurity/bloodhoundce-resources)
- [ZephrFish BloodHound Custom Queries](https://github.com/ZephrFish/Bloodhound-CustomQueries) 