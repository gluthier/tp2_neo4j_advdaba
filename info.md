
## docker
docker run --name advdaba_labo2 -p7474:7474 -p7687:7687 -v $HOME/neo4j/logs:/logs -v $HOME/neo4j/data:/data -v $HOME/neo4j/import:/var/lib/neo4j/import --memory="3g" --env NEO4J_AUTH=neo4j/testtest neo4j:latest

## K8S
serveur: rancher.kube-ext.isc.heia-fr.ch

2 sur k8
- un conteneur avec neo4j (aka le résultat final)
- un conteneur contient script avec logs start et end et qui ne termine pas (mettre à la fin une attente d'un read pour qu'il bloque et garde les logs visibles)