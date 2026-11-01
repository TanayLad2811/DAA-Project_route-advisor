import json
from abc import ABC, abstractmethod
from pathlib import Path

from app.config import settings
from app.schemas.graph import Graph, Hazard
from app.schemas.plan import PlanMetadata


class PlanRepository(ABC):
    @abstractmethod
    def save_plan(self, plan_id: str, image_bytes: bytes, metadata: PlanMetadata) -> None:
        pass

    @abstractmethod
    def get_plan_metadata(self, plan_id: str) -> PlanMetadata | None:
        pass

    @abstractmethod
    def get_plan_image_path(self, plan_id: str) -> Path | None:
        pass

    @abstractmethod
    def save_graph(self, plan_id: str, graph: Graph) -> None:
        pass

    @abstractmethod
    def get_graph(self, plan_id: str) -> Graph | None:
        pass

    @abstractmethod
    def save_hazards(self, plan_id: str, hazards: list[Hazard]) -> None:
        pass

    @abstractmethod
    def get_hazards(self, plan_id: str) -> list[Hazard]:
        pass

    @abstractmethod
    def delete_plan(self, plan_id: str) -> bool:
        pass


class DiskPlanRepository(PlanRepository):
    def __init__(self, upload_dir: Path | None = None, graph_dir: Path | None = None):
        self.upload_dir = upload_dir or settings.upload_dir
        self.graph_dir = graph_dir or settings.graph_dir
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.graph_dir.mkdir(parents=True, exist_ok=True)

    def _meta_path(self, plan_id: str) -> Path:
        return self.upload_dir / f"{plan_id}.meta.json"

    def _image_path(self, plan_id: str) -> Path:
        return self.upload_dir / f"{plan_id}.png"

    def _graph_path(self, plan_id: str) -> Path:
        return self.graph_dir / f"{plan_id}.json"

    def _hazards_path(self, plan_id: str) -> Path:
        return self.graph_dir / f"{plan_id}.hazards.json"

    def save_plan(self, plan_id: str, image_bytes: bytes, metadata: PlanMetadata) -> None:
        img_path = self._image_path(plan_id)
        img_path.write_bytes(image_bytes)
        meta_path = self._meta_path(plan_id)
        meta_path.write_text(metadata.model_dump_json(indent=2), encoding="utf-8")

    def get_plan_metadata(self, plan_id: str) -> PlanMetadata | None:
        meta_path = self._meta_path(plan_id)
        if not meta_path.exists():
            return None
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        return PlanMetadata(**data)

    def get_plan_image_path(self, plan_id: str) -> Path | None:
        img_path = self._image_path(plan_id)
        if not img_path.exists():
            return None
        return img_path

    def save_graph(self, plan_id: str, graph: Graph) -> None:
        graph_path = self._graph_path(plan_id)
        graph_path.write_text(graph.model_dump_json(indent=2), encoding="utf-8")

    def get_graph(self, plan_id: str) -> Graph | None:
        graph_path = self._graph_path(plan_id)
        if not graph_path.exists():
            return None
        data = json.loads(graph_path.read_text(encoding="utf-8"))
        return Graph(**data)

    def save_hazards(self, plan_id: str, hazards: list[Hazard]) -> None:
        hazards_path = self._hazards_path(plan_id)
        raw = [h.model_dump() for h in hazards]
        hazards_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")

    def get_hazards(self, plan_id: str) -> list[Hazard]:
        hazards_path = self._hazards_path(plan_id)
        if not hazards_path.exists():
            return []
        data = json.loads(hazards_path.read_text(encoding="utf-8"))
        return [Hazard(**h) for h in data]

    def delete_plan(self, plan_id: str) -> bool:
        deleted = False
        for p in [
            self._image_path(plan_id),
            self._meta_path(plan_id),
            self._graph_path(plan_id),
            self._hazards_path(plan_id),
        ]:
            if p.exists():
                p.unlink()
                deleted = True
        return deleted


repo: PlanRepository = DiskPlanRepository()
