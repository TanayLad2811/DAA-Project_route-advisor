import sys
from pathlib import Path
sys.path.insert(0, str(Path(r'd:/Daa project/backend')))
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
img_bytes = open(r'C:/Users/tanay/.gemini/antigravity/brain/7881c658-6647-4629-a06a-f5a871e95d67/.user_uploaded/media_1793535189515_9cde1146.png', 'rb').read()

up_res = client.post('/api/v1/plans', files={'file': ('plan.png', img_bytes, 'image/png')})
plan_id = up_res.json()['plan_id']
print('Upload:', up_res.status_code, 'Plan ID:', plan_id)

build_res = client.post(f'/api/v1/plans/{plan_id}/graph', json={'strategy': 'skeleton', 'wall_threshold': 127})
build_data = build_res.json()
graph = build_data['graph']
print('Skeleton nodes count:', len(graph['nodes']), 'edges count:', len(graph['edges']))
print('Suggested exits:', build_data['suggested_exits'])

exit_node_id = graph['nodes'][-1]['id']

for test_pt in [(100, 250), (300, 200), (500, 200), (700, 200), (900, 250)]:
    route_res = client.post(f'/api/v1/plans/{plan_id}/route', json={
        'algorithm': 'shortest_path',
        'start': list(test_pt),
        'exit_ids': [exit_node_id],
    })
    r_data = route_res.json()
    print('Route from', test_pt, 'routes:', len(r_data.get('routes', [])), 'warnings:', r_data.get('warnings'))
    if r_data.get('routes'):
        print('  Points count:', len(r_data['routes'][0]['points']), 'dist:', r_data['routes'][0]['distance_px'])

