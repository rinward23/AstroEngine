"""Hierarchical registry for AstroEngine modules.

The registry organises module → submodule → channel → subchannel
metadata so large SolarFire-derived datasets can be catalogued in a
consistent way.  Each node stores arbitrary metadata dictionaries which
are meant to describe the backing dataset (e.g., file paths, schema keys
or provenance information).  The lightweight API keeps the registry
mutable so that downstream packages can add new datasets without editing
existing Python modules, satisfying the ``no module loss`` constraint.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, MutableMapping
from dataclasses import dataclass, field

__all__ = [
    "AstroRegistry",
    "AstroModule",
    "AstroSubmodule",
    "AstroChannel",
    "AstroSubchannel",
]


@dataclass
class AstroSubchannel:
    """Leaf node representing a concrete dataset or rule collection."""

    name: str
    metadata: MutableMapping[str, object] = field(default_factory=dict)
    payload: Mapping[str, object] | None = None

    def describe(self) -> Mapping[str, object]:
        """Return a merged view of metadata and payload references."""

        data: dict[str, object] = dict(self.metadata)
        if self.payload is not None:
            data.setdefault("payload", self.payload)
        return data


@dataclass
class AstroChannel:
    """Group of closely related subchannels (e.g., core/extended aspects)."""

    name: str
    metadata: MutableMapping[str, object] = field(default_factory=dict)
    subchannels: dict[str, AstroSubchannel] = field(default_factory=dict)

    def register_subchannel(
        self,
        name: str,
        *,
        metadata: Mapping[str, object] | None = None,
        payload: Mapping[str, object] | None = None,
    ) -> AstroSubchannel:
        if name in self.subchannels:
            sub = self.subchannels[name]
            if metadata:
                sub.metadata.update(metadata)
            if payload is not None:
                sub.payload = payload
            return sub
        subchannel = AstroSubchannel(
            name=name, metadata=dict(metadata or {}), payload=payload
        )
        self.subchannels[name] = subchannel
        return subchannel

    def get_subchannel(self, name: str) -> AstroSubchannel:
        return self.subchannels[name]

    def iter_subchannels(self) -> Iterable[AstroSubchannel]:
        return self.subchannels.values()


@dataclass
class AstroSubmodule:
    """Intermediate node used to segment modules into logical domains."""

    name: str
    metadata: MutableMapping[str, object] = field(default_factory=dict)
    channels: dict[str, AstroChannel] = field(default_factory=dict)

    def register_channel(
        self,
        name: str,
        *,
        metadata: Mapping[str, object] | None = None,
    ) -> AstroChannel:
        if name in self.channels:
            channel = self.channels[name]
            if metadata:
                channel.metadata.update(metadata)
            return channel
        channel = AstroChannel(name=name, metadata=dict(metadata or {}))
        self.channels[name] = channel
        return channel

    def get_channel(self, name: str) -> AstroChannel:
        return self.channels[name]

    def iter_channels(self) -> Iterable[AstroChannel]:
        return self.channels.values()


@dataclass
class AstroModule:
    """Top-level container representing a major AstroEngine capability."""

    name: str
    metadata: MutableMapping[str, object] = field(default_factory=dict)
    submodules: dict[str, AstroSubmodule] = field(default_factory=dict)

    def register_submodule(
        self,
        name: str,
        *,
        metadata: Mapping[str, object] | None = None,
    ) -> AstroSubmodule:
        if name in self.submodules:
            submodule = self.submodules[name]
            if metadata:
                submodule.metadata.update(metadata)
            return submodule
        submodule = AstroSubmodule(name=name, metadata=dict(metadata or {}))
        self.submodules[name] = submodule
        return submodule

    def get_submodule(self, name: str) -> AstroSubmodule:
        return self.submodules[name]

    def iter_submodules(self) -> Iterable[AstroSubmodule]:
        return self.submodules.values()


class AstroRegistry:
    """Mutable registry mapping module names to :class:`AstroModule` objects."""

    def __init__(self) -> None:
        self._modules: dict[str, AstroModule] = {}

    def register_module(
        self,
        name: str,
        *,
        metadata: Mapping[str, object] | None = None,
    ) -> AstroModule:
        if name in self._modules:
            module = self._modules[name]
            if metadata:
                module.metadata.update(metadata)
            return module
        module = AstroModule(name=name, metadata=dict(metadata or {}))
        self._modules[name] = module
        return module

    def get_module(self, name: str) -> AstroModule:
        return self._modules[name]

    def iter_modules(self) -> Iterable[AstroModule]:
        return self._modules.values()

    def as_dict(self) -> dict[str, Mapping[str, object]]:
        """Return a serialisable snapshot of the registry hierarchy."""

        snapshot: dict[str, Mapping[str, object]] = {}
        for module_name, module in self._modules.items():
            module_payload: dict[str, object] = {
                "metadata": dict(module.metadata),
                "submodules": {},
            }
            for submodule_name, submodule in module.submodules.items():
                submodule_payload: dict[str, object] = {
                    "metadata": dict(submodule.metadata),
                    "channels": {},
                }
                for channel_name, channel in submodule.channels.items():
                    channel_payload: dict[str, object] = {
                        "metadata": dict(channel.metadata),
                        "subchannels": {},
                    }
                    for subchannel_name, subchannel in channel.subchannels.items():
                        channel_payload["subchannels"][
                            subchannel_name
                        ] = subchannel.describe()
                    submodule_payload["channels"][channel_name] = channel_payload
                module_payload["submodules"][submodule_name] = submodule_payload
            snapshot[module_name] = module_payload
        return snapshot
