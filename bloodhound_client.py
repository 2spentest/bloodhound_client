import requests
import hmac
import hashlib
import base64
import datetime
import json
import yaml
import os
import argparse
import time
from typing import Optional, Dict, Any, List, Union
from pathlib import Path

class BloodHoundClient:
    def __init__(self, base_url: str, token_id: str, token_key: str, rate_limit_delay: float = 0.5):
        """
        Initialize the BloodHound API client.
        
        Args:
            base_url: The base URL of your BloodHound instance (e.g., 'http://localhost:8080')
            token_id: Your BloodHound API token ID
            token_key: Your BloodHound API token key
            rate_limit_delay: Delay between requests in seconds (default: 0.5)
        """
        self.base_url = base_url.rstrip('/')
        self._credentials = type('Credentials', (), {'token_id': token_id, 'token_key': token_key})()
        self.rate_limit_delay = rate_limit_delay
        self.last_request_time = 0

    def _request(self, method: str, uri: str, body: Optional[bytes] = None) -> requests.Response:
        """
        Make an authenticated request to the BloodHound API with rate limiting.
        """
        # Implement rate limiting
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last_request)
        
        # Initialize HMAC-SHA-256 digester
        digester = hmac.new(self._credentials.token_key.encode(), None, hashlib.sha256)

        # Create operation key (method + URI)
        digester.update(f'{method}{uri}'.encode())
        digester = hmac.new(digester.digest(), None, hashlib.sha256)

        # Add date key (RFC3339 datetime truncated to hour)
        datetime_formatted = datetime.datetime.now().astimezone().isoformat('T')
        digester.update(datetime_formatted[:13].encode())
        digester = hmac.new(digester.digest(), None, hashlib.sha256)

        # Add body if present
        if body is not None:
            digester.update(body)

        # Make the request with authentication headers
        response = requests.request(
            method=method,
            url=f"{self.base_url}{uri}",
            headers={
                'User-Agent': 'bloodhound-python-client',
                'Authorization': f'bhesignature {self._credentials.token_id}',
                'RequestDate': datetime_formatted,
                'Signature': base64.b64encode(digester.digest()).decode(),
                'Content-Type': 'application/json',
            },
            data=body,
        )
        
        # Update last request time
        self.last_request_time = time.time()
        
        return response

    def import_custom_query(self, query_name: str, query: str, description: str = "") -> Dict[str, Any]:
        """
        Import a custom Cypher query into BloodHound.
        
        Args:
            query_name: Name of the custom query
            query: The Cypher query string
            description: Optional description of the query
            
        Returns:
            Dict containing the API response
        """
        # BloodHound CE uses /api/v2/saved-queries endpoint
        uri = '/api/v2/saved-queries'
        body = {
            'name': query_name,
            'query': query,
            'description': description
        }
        
        try:
            response = self._request('POST', uri, body=json.dumps(body).encode())
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:  # Too Many Requests
                print(f"Rate limit hit, waiting {self.rate_limit_delay * 2} seconds...")
                time.sleep(self.rate_limit_delay * 2)  # Double the delay when we hit the limit
                # Retry the request
                response = self._request('POST', uri, body=json.dumps(body).encode())
                response.raise_for_status()
                return response.json()
            print(f"Error details for query '{query_name}':")
            print(f"Status code: {e.response.status_code}")
            print(f"Response: {e.response.text}")
            raise

    def import_queries_from_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Import queries from a local file.
        Supports JSON, YAML, and plain text formats.
        
        Args:
            file_path: Path to the file containing queries
            
        Returns:
            List of results from importing queries
        """
        results = []
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Try to parse as JSON first
        try:
            queries = json.loads(content)
            if isinstance(queries, list):
                for query in queries:
                    result = self.import_custom_query(
                        query.get('name', 'Unnamed Query'),
                        query.get('query', ''),
                        query.get('description', '')
                    )
                    results.append(result)
            elif isinstance(queries, dict):
                result = self.import_custom_query(
                    queries.get('name', 'Unnamed Query'),
                    queries.get('query', ''),
                    queries.get('description', '')
                )
                results.append(result)
        except json.JSONDecodeError:
            # Try to parse as YAML
            try:
                queries = yaml.safe_load(content)
                if isinstance(queries, list):
                    for query in queries:
                        result = self.import_custom_query(
                            query.get('name', 'Unnamed Query'),
                            query.get('query', ''),
                            query.get('description', '')
                        )
                        results.append(result)
                elif isinstance(queries, dict):
                    result = self.import_custom_query(
                        queries.get('name', 'Unnamed Query'),
                        queries.get('query', ''),
                        queries.get('description', '')
                    )
                    results.append(result)
            except yaml.YAMLError:
                # Treat as plain text with a single query
                result = self.import_custom_query(
                    file_path.stem,
                    content.strip(),
                    f"Query imported from {file_path.name}"
                )
                results.append(result)

        return results

    def import_queries_from_github(self, repo_url: str, branch: str = "main", path: str = "") -> List[Dict[str, Any]]:
        """
        Import queries from a GitHub repository.
        
        Args:
            repo_url: GitHub repository URL
            branch: Branch name (default: main)
            path: Path within the repository (default: root)
            
        Returns:
            List of results from importing queries
        """
        # Convert GitHub URL to raw content URL
        raw_url = repo_url.replace("github.com", "raw.githubusercontent.com")
        if not raw_url.endswith("/"):
            raw_url += "/"
        raw_url += f"{branch}/{path}"

        # Get repository contents
        response = requests.get(raw_url)
        response.raise_for_status()
        
        results = []
        if path.endswith(('.json', '.yaml', '.yml', '.txt', '.cypher')):
            # Single file
            result = self.import_queries_from_file(response.text)
            results.extend(result)
        else:
            # Directory listing
            for item in response.json():
                if item['type'] == 'file' and item['name'].endswith(('.json', '.yaml', '.yml', '.txt', '.cypher')):
                    file_url = item['download_url']
                    file_response = requests.get(file_url)
                    file_response.raise_for_status()
                    
                    # Save to temporary file
                    temp_file = Path(f"temp_{item['name']}")
                    with open(temp_file, 'w', encoding='utf-8') as f:
                        f.write(file_response.text)
                    
                    try:
                        result = self.import_queries_from_file(str(temp_file))
                        results.extend(result)
                    finally:
                        # Clean up temporary file
                        temp_file.unlink()

        return results

def import_queries_from_json_url(client: BloodHoundClient, json_url: str) -> List[Dict[str, Any]]:
    """
    Import queries from a JSON URL (e.g., GitHub raw content URL).
    
    Args:
        client: BloodHoundClient instance
        json_url: URL to the JSON file containing queries
        
    Returns:
        List of results from importing queries
    """
    try:
        # Convert GitHub blob URL to raw content URL if needed
        if 'github.com' in json_url and '/blob/' in json_url:
            json_url = json_url.replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')
        
        response = requests.get(json_url)
        response.raise_for_status()
        queries_data = response.json()
        
        results = []
        # Handle different JSON structures
        if 'queries' in queries_data:
            # Compass/ZephrFish format
            for query_group in queries_data.get('queries', []):
                category = query_group.get('category', 'Uncategorized')
                for query_item in query_group.get('queryList', []):
                    if query_item.get('final', False):
                        query_name = f"{query_group['name']} - {category}"
                        query = query_item.get('query', '')
                        description = f"Category: {category}"
                        
                        try:
                            result = client.import_custom_query(query_name, query, description)
                            results.append(result)
                            print(f"Imported query: {query_name}")
                        except Exception as e:
                            print(f"Error importing query {query_name}: {str(e)}")
        else:
            # Simple array format
            for query_item in queries_data:
                query_name = query_item.get('name', 'Unnamed Query')
                query = query_item.get('query', '')
                description = query_item.get('description', '')
                
                try:
                    result = client.import_custom_query(query_name, query, description)
                    results.append(result)
                    print(f"Imported query: {query_name}")
                except Exception as e:
                    print(f"Error importing query {query_name}: {str(e)}")
        
        return results
    except Exception as e:
        print(f"Error fetching queries from URL: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description='BloodHound CE Custom Query Importer')
    parser.add_argument('--url', default="http://localhost:8080",
                      help='BloodHound instance URL (default: http://localhost:8080)')
    parser.add_argument('--token-id', required=True,
                      help='BloodHound API token ID')
    parser.add_argument('--token-key', required=True,
                      help='BloodHound API token key')
    parser.add_argument('--json-url',
                      help='URL to JSON file containing queries (e.g., GitHub raw content URL)')
    parser.add_argument('--github', 
                      help='Import queries from a GitHub repository URL')
    parser.add_argument('--file',
                      help='Import queries from a local file')
    parser.add_argument('--branch', default='main',
                      help='GitHub branch name (default: main)')
    parser.add_argument('--path', default='',
                      help='Path within GitHub repository or local directory')
    parser.add_argument('--rate-limit', type=float, default=0.5,
                      help='Delay between requests in seconds (default: 0.5)')

    args = parser.parse_args()

    # Initialize the client with rate limiting
    client = BloodHoundClient(args.url, args.token_id, args.token_key, rate_limit_delay=args.rate_limit)

    results = []

    # Import from JSON URL if specified
    if args.json_url:
        print(f"Importing queries from JSON URL: {args.json_url}")
        results.extend(import_queries_from_json_url(client, args.json_url))

    # Import from GitHub if specified
    if args.github:
        print(f"Importing queries from GitHub repository: {args.github}")
        try:
            github_results = client.import_queries_from_github(
                args.github,
                branch=args.branch,
                path=args.path
            )
            results.extend(github_results)
        except Exception as e:
            print(f"Error importing from GitHub: {e}")

    # Import from local file if specified
    if args.file:
        print(f"Importing queries from local file: {args.file}")
        try:
            file_results = client.import_queries_from_file(args.file)
            results.extend(file_results)
        except Exception as e:
            print(f"Error importing from local file: {e}")

    # Print summary
    print(f"\nImport Summary:")
    print(f"Total queries imported: {len(results)}")

if __name__ == "__main__":
    main() 