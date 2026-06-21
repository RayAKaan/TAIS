import json
import numpy as np
from sklearn.cluster import KMeans
from collections import defaultdict


def get_topology_feature(mean_sig):
    # sig index mapping:
    # 0: net, 1: valid, 2: ent_add, 3: ent_rem, 4: ent_mod, 5: rel_add,
    # 6: rel_rem, 7: rel_mod, 8: magnitude
    net = mean_sig[0]
    valid = mean_sig[1]
    has_ent = 1.0 if (mean_sig[2] + mean_sig[3] + mean_sig[4]) > 0 else 0.0
    has_rel = 1.0 if (mean_sig[5] + mean_sig[6] + mean_sig[7]) > 0 else 0.0
    valence = 1.0 if net > 0.1 else (-1.0 if net < -0.1 else 0.0)

    return [valence, valid, has_ent, has_rel]


def discover_roles(json_path, k=5):
    with open(json_path, "r") as f:
        data = json.load(f)

    grouped = defaultdict(list)
    for entry in data:
        key = (entry["domain"], entry["action"])
        grouped[key].append(entry["signature"])

    action_keys = list(grouped.keys())
    X = np.array([
        get_topology_feature(np.mean(grouped[k], axis=0))
        for k in action_keys
    ])

    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X)

    clusters = defaultdict(list)
    for i, label in enumerate(labels):
        clusters[int(label)].append(action_keys[i])

    return clusters


if __name__ == "__main__":
    discovered = discover_roles("structural_signatures.json", k=5)
    print("=== DISCOVERED CROSS-DOMAIN ROLES (TOPOLOGY) ===")
    mapping = {}
    for cid, members in discovered.items():
        print(f"\nCluster {cid}:")
        for domain, action in sorted(members):
            print(f"  [{domain.upper()}] {action}")
            mapping[f"{domain}:{action}"] = cid

    with open("discovered_role_mapping.json", "w") as f:
        json.dump(mapping, f, indent=2)
