from neo4j import GraphDatabase
import ijson
import re

# Credentials
uri = "bolt://localhost:7687"
user = "neo4j"
password = "testtest"

driver = GraphDatabase.driver(uri, auth=(user, password))

def clean_mongo_extended_json_obj(obj):
    """
    Recursively clean MongoDB extended types in a parsed JSON object.
    """
    if isinstance(obj, dict):
        return {
            k: clean_mongo_extended_json_obj(v)
            for k, v in obj.items()
        }
    elif isinstance(obj, list):
        return [clean_mongo_extended_json_obj(item) for item in obj]
    elif isinstance(obj, str):
        # Convert MongoDB-like extended syntax in strings
        obj = re.sub(r'Number(Int|Long)?\((\d+)\)', r'\2', obj)
        obj = re.sub(r'ObjectId\("([^"]+)"\)', r'"\1"', obj)
        obj = re.sub(r'ISODate\("([^"]+)"\)', r'"\1"', obj)
        return obj
    else:
        return obj

def create_graph(tx, paper):
    tx.run("""
        MERGE (p:Paper {_id: $pid, title: $title, year: $year})
        WITH p
        MERGE (v:Venue {_id: $vid, name: $vname})
        MERGE (p)-[:PUBLISHED_IN]->(v)
    """, pid=paper['_id'], title=paper['title'], year=paper.get('year', 0),
         vid=paper.get('venue', {}).get('_id', 'unknown'), vname=paper.get('venue', {}).get('raw', 'Unknown'))

    for author in paper.get('authors', []):
        tx.run("""
            MERGE (a:Author {_id: $aid, name: $name})
            MERGE (a)-[:WROTE]->(p:Paper {_id: $pid})
        """, aid=author['_id'], name=author['name'], pid=paper['_id'])

    for kw in paper.get('keywords', []):
        tx.run("""
            MERGE (k:Keyword {name: $kw})
            MERGE (p:Paper {_id: $pid})
            MERGE (p)-[:HAS_KEYWORD]->(k)
        """, kw=kw, pid=paper['_id'])

    for fos in paper.get('fos', []):
        tx.run("""
            MERGE (f:FieldOfStudy {name: $fos})
            MERGE (p:Paper {_id: $pid})
            MERGE (p)-[:HAS_FOS]->(f)
        """, fos=fos, pid=paper['_id'])

    for ref in paper.get('references', []):
        tx.run("""
            MERGE (p1:Paper {_id: $pid})
            MERGE (p2:Paper {_id: $refid})
            MERGE (p1)-[:CITES]->(p2)
        """, pid=paper['_id'], refid=ref)

with open("import/test.json", "rb") as f:
    for article in ijson.items(f, "item"):
        clean_article = clean_mongo_extended_json_obj(article)
        with driver.session() as session:
            session.execute_write(create_graph, clean_article)

driver.close()
