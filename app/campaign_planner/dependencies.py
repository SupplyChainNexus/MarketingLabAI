"""Deterministic Campaign Asset dependency planning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.campaign_planner.assets import (
    CampaignAsset,
    CampaignAssetStatus,
)


@dataclass(frozen=True, slots=True)
class CampaignDependencyIssue:
    """A structured problem in a campaign dependency graph."""

    code: str
    asset_id: str
    message: str


class CampaignDependencyPlanner:
    """Validate and order campaign assets without provider dependencies."""

    @staticmethod
    def _asset_map(assets: Iterable[CampaignAsset]) -> dict[str, CampaignAsset]:
        if isinstance(assets, (str, bytes)):
            raise TypeError("assets must be an iterable of CampaignAsset values.")
        asset_map: dict[str, CampaignAsset] = {}
        for asset in assets:
            if not isinstance(asset, CampaignAsset):
                raise TypeError("assets must contain CampaignAsset values.")
            if asset.asset_id in asset_map:
                raise ValueError(f"Duplicate asset_id: {asset.asset_id}.")
            asset_map[asset.asset_id] = asset
        return asset_map

    def validate(
        self,
        assets: Iterable[CampaignAsset],
    ) -> tuple[CampaignDependencyIssue, ...]:
        asset_map = self._asset_map(assets)
        issues: list[CampaignDependencyIssue] = []

        for asset in asset_map.values():
            for dependency_id in asset.dependency_ids:
                if dependency_id not in asset_map:
                    issues.append(
                        CampaignDependencyIssue(
                            code="missing_dependency",
                            asset_id=asset.asset_id,
                            message=(f"Dependency '{dependency_id}' does not exist."),
                        )
                    )

        if not issues:
            try:
                self.execution_order(asset_map.values())
            except ValueError as error:
                issues.append(
                    CampaignDependencyIssue(
                        code="dependency_cycle",
                        asset_id="",
                        message=str(error),
                    )
                )

        return tuple(issues)

    def execution_order(
        self,
        assets: Iterable[CampaignAsset],
    ) -> tuple[CampaignAsset, ...]:
        asset_map = self._asset_map(assets)
        for asset in asset_map.values():
            missing = set(asset.dependency_ids) - set(asset_map)
            if missing:
                names = ", ".join(sorted(missing))
                raise ValueError(f"Missing campaign asset dependencies: {names}.")

        indegree = {asset_id: 0 for asset_id in asset_map}
        dependants = {asset_id: [] for asset_id in asset_map}
        for asset in asset_map.values():
            indegree[asset.asset_id] = len(asset.dependency_ids)
            for dependency_id in asset.dependency_ids:
                dependants[dependency_id].append(asset.asset_id)

        ready = sorted(
            (asset for asset in asset_map.values() if indegree[asset.asset_id] == 0),
            key=lambda asset: (asset.priority, asset.name.casefold(), asset.asset_id),
        )
        ordered: list[CampaignAsset] = []

        while ready:
            current = ready.pop(0)
            ordered.append(current)
            for dependant_id in sorted(dependants[current.asset_id]):
                indegree[dependant_id] -= 1
                if indegree[dependant_id] == 0:
                    ready.append(asset_map[dependant_id])
                    ready.sort(
                        key=lambda asset: (
                            asset.priority,
                            asset.name.casefold(),
                            asset.asset_id,
                        )
                    )

        if len(ordered) != len(asset_map):
            raise ValueError("Campaign asset dependency graph contains a cycle.")

        return tuple(ordered)

    def blocked_assets(
        self,
        assets: Iterable[CampaignAsset],
    ) -> tuple[CampaignAsset, ...]:
        asset_map = self._asset_map(assets)
        blocked: list[CampaignAsset] = []
        completed = {
            asset.asset_id
            for asset in asset_map.values()
            if asset.status is CampaignAssetStatus.COMPLETED
        }
        for asset in asset_map.values():
            if any(
                dependency_id not in completed for dependency_id in asset.dependency_ids
            ):
                blocked.append(asset)
        return tuple(sorted(blocked, key=lambda asset: asset.name.casefold()))
