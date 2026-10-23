"""Tests for OpenAPI 3.1 schema specification compliance."""
import os
import yaml


def test_openapi_yaml_specification():
    """Verify openapi.yaml is valid OpenAPI 3.1 and covers all endpoints."""
    assert os.path.exists("openapi.yaml"), "openapi.yaml file is missing"

    with open("openapi.yaml", "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    assert spec.get("openapi") == "3.1.0"
    assert "info" in spec
    assert "paths" in spec

    paths = spec["paths"]
    assert "/api/v1/music/jobs" in paths
    assert "post" in paths["/api/v1/music/jobs"]

    assert "/api/v1/jobs/{job_id}" in paths
    assert "get" in paths["/api/v1/jobs/{job_id}"]

    assert "/health" in paths
    assert "/ready" in paths
