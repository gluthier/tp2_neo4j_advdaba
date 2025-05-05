from neo4j import GraphDatabase
import json
import re

# Credentials
uri = "bolt://localhost:7687"
user = "neo4j"
password = "testtest"

INPUT_FILE = "import/test.json"

driver = GraphDatabase.driver(uri, auth=(user, password))

def create_graph(tx, paper):
    # Create ARTICLE node
    tx.run("""
        MERGE (a:ARTICLE {_id: $pid})
        SET a.title = $title
    """, pid=paper['_id'], title=paper['title'])

    # Create AUTHOR nodes and AUTHORED relationships
    for author in paper.get('authors', []):
        tx.run("""
            MERGE (au:AUTHOR {_id: $aid})
            SET au.name = $name
            MERGE (a:ARTICLE {_id: $pid})
            MERGE (au)-[:AUTHORED]->(a)
        """, aid=author['_id'], name=author['name'], pid=paper['_id'])

    # Create CITES relationships to other ARTICLE nodes
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
    # Quote unquoted keys (e.g., _id: → "_id":
    text = re.sub(r'([{,])\s*([a-zA-Z0-9_]+)\s*:', r'\1 "\2":', text)
    return text

def stream_articles(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        buf = ""
        depth = 0
        inside_object = False

        for line in f:
            line = line.strip()

            # Skip JSON array brackets or commas separating objects
            if line in {"[", "]", ","}:
                continue

            # Start of a JSON object
            if "{" in line:
                depth += line.count("{")
                inside_object = True

            if inside_object:
                buf += line + "\n"

            if "}" in line:
                depth -= line.count("}")
                if depth == 0:
                    # Clean and parse single object
                    cleaned = clean_extended_json(buf.strip().rstrip(","))
                    try:
                        yield json.loads(cleaned)
                    except Exception as e:
                        print(f"❌ Failed to parse article: {e}")
                        # Uncomment to debug:
                        # print(cleaned)
                    buf = ""
                    inside_object = False

count = 0
for article in stream_articles(INPUT_FILE):
    try:
        with driver.session() as session:
            session.execute_write(create_graph, article)
        count += 1
        if count % 100 == 0:
            print(f"✅ Imported {count} articles...")
    except Exception as e:
        print(f"❌ Failed to import article #{count}: {e}")

print(f"✅ DONE: Imported {count} articles total.")

driver.close()
