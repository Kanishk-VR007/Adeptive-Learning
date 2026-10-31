import pytest
from fastapi.testclient import TestClient
from app.models.syllabus import DifficultyLevel


@pytest.fixture
def graph_setup(teacher_client: TestClient):
    """Set up a subject, chapter, and 4 concepts for graph testing."""
    s = teacher_client.post("/api/v1/subjects", json={"code": "CALC", "name": "Calculus"}).json()
    ch = teacher_client.post("/api/v1/chapters", json={"subject_id": s["id"], "chapter_number": 1, "title": "Calculus Core"}).json()

    concepts = []
    names = [
        ("FUNCTIONS", "Foundations of Functions", DifficultyLevel.BEGINNER),
        ("LIMITS", "Limits & Continuity", DifficultyLevel.BEGINNER),
        ("DERIVATIVES", "Differential Calculus", DifficultyLevel.INTERMEDIATE),
        ("INTEGRALS", "Integral Calculus", DifficultyLevel.ADVANCED)
    ]

    for code, name, diff in names:
        c = teacher_client.post("/api/v1/concepts", json={
            "concept_code": f"CALC_{code}",
            "subject_id": s["id"],
            "chapter_id": ch["id"],
            "name": name,
            "description": f"Mastery of {name}",
            "difficulty_level": diff.value,
            "learning_objectives": [f"Learn {name}"]
        }).json()
        concepts.append(c)

    return {
        "subject": s,
        "chapter": ch,
        "c_functions": concepts[0],
        "c_limits": concepts[1],
        "c_derivatives": concepts[2],
        "c_integrals": concepts[3]
    }


def test_add_valid_prerequisite(teacher_client: TestClient, graph_setup):
    c_func = graph_setup["c_functions"]
    c_lim = graph_setup["c_limits"]

    # Limits requires Functions
    payload = {
        "concept_id": c_lim["id"],
        "prerequisite_id": c_func["id"],
        "relationship_type": "STRICT"
    }
    response = teacher_client.post("/api/v1/graph/prerequisites", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["concept_id"] == c_lim["id"]
    assert data["prerequisite_id"] == c_func["id"]


def test_student_forbidden_to_add_prerequisite(student_client: TestClient, graph_setup):
    payload = {
        "concept_id": graph_setup["c_limits"]["id"],
        "prerequisite_id": graph_setup["c_functions"]["id"],
        "relationship_type": "STRICT"
    }
    response = student_client.post("/api/v1/graph/prerequisites", json=payload)
    assert response.status_code == 403


def test_reject_self_loop(teacher_client: TestClient, graph_setup):
    c_lim = graph_setup["c_limits"]
    payload = {
        "concept_id": c_lim["id"],
        "prerequisite_id": c_lim["id"],
        "relationship_type": "STRICT"
    }
    response = teacher_client.post("/api/v1/graph/prerequisites", json=payload)
    assert response.status_code == 400
    assert "itself" in str(response.json())


def test_reject_direct_2_node_cycle(teacher_client: TestClient, graph_setup):
    c_lim = graph_setup["c_limits"]
    c_deriv = graph_setup["c_derivatives"]

    # 1. Derivatives requires Limits
    res1 = teacher_client.post("/api/v1/graph/prerequisites", json={
        "concept_id": c_deriv["id"],
        "prerequisite_id": c_lim["id"]
    })
    assert res1.status_code == 201

    # 2. Attempt: Limits requires Derivatives (would form 2-cycle)
    res2 = teacher_client.post("/api/v1/graph/prerequisites", json={
        "concept_id": c_lim["id"],
        "prerequisite_id": c_deriv["id"]
    })
    assert res2.status_code == 400
    err = res2.json()["detail"]
    assert "circular dependency cycle" in err["message"]
    assert err["cycle_path"] == [c_lim["id"], c_deriv["id"], c_lim["id"]]


def test_reject_multi_step_transitive_cycle(teacher_client: TestClient, graph_setup):
    c1 = graph_setup["c_functions"]
    c2 = graph_setup["c_limits"]
    c3 = graph_setup["c_derivatives"]
    c4 = graph_setup["c_integrals"]

    # Chain: c2 requires c1, c3 requires c2, c4 requires c3
    # Chain in learning flow: c1 -> c2 -> c3 -> c4
    teacher_client.post("/api/v1/graph/prerequisites", json={"concept_id": c2["id"], "prerequisite_id": c1["id"]})
    teacher_client.post("/api/v1/graph/prerequisites", json={"concept_id": c3["id"], "prerequisite_id": c2["id"]})
    teacher_client.post("/api/v1/graph/prerequisites", json={"concept_id": c4["id"], "prerequisite_id": c3["id"]})

    # Attempt to make c1 require c4 (closing cycle c1 -> c4 -> c3 -> c2 -> c1)
    res = teacher_client.post("/api/v1/graph/prerequisites", json={
        "concept_id": c1["id"],
        "prerequisite_id": c4["id"]
    })
    assert res.status_code == 400
    err = res.json()["detail"]
    assert err["cycle_path"] == [c1["id"], c4["id"], c3["id"], c2["id"], c1["id"]]


def test_preflight_validation_endpoint(student_client: TestClient, teacher_client: TestClient, graph_setup):
    c1 = graph_setup["c_functions"]
    c2 = graph_setup["c_limits"]

    # 1. Before edge exists, validate is_valid = True
    val_before = student_client.post("/api/v1/graph/validate-link", json={
        "concept_id": c2["id"],
        "prerequisite_id": c1["id"]
    })
    assert val_before.status_code == 200
    assert val_before.json()["is_valid"] is True
    assert val_before.json()["would_form_cycle"] is False

    # Add the edge
    teacher_client.post("/api/v1/graph/prerequisites", json={
        "concept_id": c2["id"],
        "prerequisite_id": c1["id"]
    })

    # 2. Check inverse edge: should flag would_form_cycle = True
    val_after = student_client.post("/api/v1/graph/validate-link", json={
        "concept_id": c1["id"],
        "prerequisite_id": c2["id"]
    })
    assert val_after.status_code == 200
    assert val_after.json()["is_valid"] is False
    assert val_after.json()["would_form_cycle"] is True
    assert val_after.json()["cycle_path"] == [c1["id"], c2["id"], c1["id"]]


def test_topological_learning_path(student_client: TestClient, teacher_client: TestClient, graph_setup):
    c1 = graph_setup["c_functions"]
    c2 = graph_setup["c_limits"]
    c3 = graph_setup["c_derivatives"]
    c4 = graph_setup["c_integrals"]

    # Setup pipeline: Integrals (c4) requires Derivatives (c3); Derivatives (c3) requires Limits (c2); Limits (c2) requires Functions (c1)
    teacher_client.post("/api/v1/graph/prerequisites", json={"concept_id": c2["id"], "prerequisite_id": c1["id"]})
    teacher_client.post("/api/v1/graph/prerequisites", json={"concept_id": c3["id"], "prerequisite_id": c2["id"]})
    teacher_client.post("/api/v1/graph/prerequisites", json={"concept_id": c4["id"], "prerequisite_id": c3["id"]})

    # Request learning path for Integrals (c4)
    path_res = student_client.get(f"/api/v1/graph/concepts/{c4['id']}/learning-path")
    assert path_res.status_code == 200
    data = path_res.json()
    assert data["target_concept_id"] == c4["id"]
    assert data["total_steps"] == 4

    # Order must be strictly: c1 -> c2 -> c3 -> c4
    sequence_ids = [step["id"] for step in data["learning_sequence"]]
    assert sequence_ids == [c1["id"], c2["id"], c3["id"], c4["id"]]


def test_subject_graph_retrieval(student_client: TestClient, teacher_client: TestClient, graph_setup):
    s = graph_setup["subject"]
    c1 = graph_setup["c_functions"]
    c2 = graph_setup["c_limits"]

    teacher_client.post("/api/v1/graph/prerequisites", json={"concept_id": c2["id"], "prerequisite_id": c1["id"]})

    graph_res = student_client.get(f"/api/v1/graph/subject/{s['id']}")
    assert graph_res.status_code == 200
    data = graph_res.json()
    assert data["subject_id"] == s["id"]
    assert data["total_nodes"] == 4
    assert data["total_edges"] == 1
    assert data["edges"][0]["from_concept_id"] == c1["id"]
    assert data["edges"][0]["to_concept_id"] == c2["id"]


def test_remove_prerequisite(teacher_client: TestClient, graph_setup):
    c1 = graph_setup["c_functions"]
    c2 = graph_setup["c_limits"]

    teacher_client.post("/api/v1/graph/prerequisites", json={"concept_id": c2["id"], "prerequisite_id": c1["id"]})

    # Delete link
    del_res = teacher_client.delete(f"/api/v1/graph/prerequisites/{c2['id']}/{c1['id']}")
    assert del_res.status_code == 204

    # Deleting again returns 404
    del_res2 = teacher_client.delete(f"/api/v1/graph/prerequisites/{c2['id']}/{c1['id']}")
    assert del_res2.status_code == 404
