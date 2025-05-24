from neo4j import GraphDatabase
import argparse
import json
import re

# Credentials
uri = "bolt://localhost:7687"
user = "neo4j"
password = "testtest"

DEFAULT_INPUT_FILE = "import/biggertest.json"

driver = GraphDatabase.driver(uri, auth=(user, password))

def create_graph(tx, paper):
    if '_id' not in paper or 'title' not in paper:
        print(f"Skipping article due to missing keys: {paper.keys()}")
        return
    
    tx.run("""
        MERGE (a:ARTICLE {_id: $pid})
        SET a.title = $title
    """, pid=paper['_id'], title=paper['title'])

    for author in paper.get('authors', []):
        if '_id' not in author or 'name' not in author:
            print(f"Skipping author due to missing keys: {author}")
            continue

        tx.run("""
            MERGE (au:AUTHOR {_id: $aid})
            SET au.name = $name
            MERGE (a:ARTICLE {_id: $pid})
            MERGE (au)-[:AUTHORED]->(a)
        """, aid=author['_id'], name=author['name'], pid=paper['_id'])

    for ref in paper.get('references', []):
        tx.run("""
            MERGE (a1:ARTICLE {_id: $pid})
            MERGE (a2:ARTICLE {_id: $refid})
            MERGE (a1)-[:CITES]->(a2)
        """, pid=paper['_id'], refid=ref)

def clean_extended_json(text):
    text = re.sub(r'Number(Int|Long)?\((\d+)\)', r'\2', text)
    text = re.sub(r'ObjectId\("([^"]+)"\)', r'"\1"', text)
    text = re.sub(r'ISODate\("([^"]+)"\)', r'"\1"', text)
    text = re.sub(r'([{,])\s*([a-zA-Z0-9_]+)\s*:', r'\1 "\2":', text)
    return text

def stream_articles(file_path, max_articles):
    with open(file_path, "r", encoding="utf-8") as f:
        buf = ""
        depth = 0
        inside_object = False
        count = 0

        for line in f:
            line = line.strip()

            if "{" in line:
                depth += line.count("{")
                inside_object = True

            if inside_object:
                buf += line + "\n"

            if "}" in line:
                depth -= line.count("}")
                if depth == 0:
                    cleaned = clean_extended_json(buf.strip().rstrip(","))                            
                    try:
                        yield json.loads(cleaned)
                        count += 1
                        if max_articles is not None and count >= max_articles:
                            break
                    except Exception as e:
                        print(f"Failed to parse article: {e}")
                    buf = ""
                    inside_object = False


def main():
    parser = argparse.ArgumentParser(description="Import articles into Neo4j")
    parser.add_argument('--input', type=str, default=DEFAULT_INPUT_FILE, help='Input JSON file path')
    parser.add_argument('--n', type=int, default=None, help='Optional number of articles to import (default: all)')	
    args = parser.parse_args()

    count = 0
    for article in stream_articles(args.input, args.n):
        try:
            with driver.session() as session:
                session.execute_write(create_graph, article)
            count += 1
            if count % 100 == 0:
                print(f"Imported {count} articles...")
        except Exception as e:
            print(f"Failed to import article #{count}: {e}")

    print(f"DONE: Imported {count} articles total.")

    driver.close()


if __name__ == '__main__':
    main()
