from empresa_gpt.ai import AIRequest
from empresa_gpt.analytics import AnalyticsEvent
from empresa_gpt.core.config import PlatformConfig
from empresa_gpt.monitoring import HealthStatus
from empresa_gpt.security import SecurityDecision
from empresa_gpt.services import ServiceCommand, ServiceResult
from empresa_gpt.storage import StorageQuery


def test_phase2_contracts_are_disabled_by_default():
    config = PlatformConfig()
    decision = SecurityDecision()
    command = ServiceCommand(name="noop")
    result = ServiceResult()
    status = HealthStatus(name="noop")

    assert config.service_enabled is False
    assert decision.allowed is False
    assert command.dry_run is True
    assert result.accepted is False
    assert status.status == "unknown"


def test_phase2_contracts_are_importable_without_runtime_dependencies():
    request = AIRequest(prompt="hello")
    event = AnalyticsEvent(name="view", resource="docs")
    query = StorageQuery(collection="docs")

    assert request.provider == "ollama"
    assert event.properties == {}
    assert query.limit == 100

