from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Self, Sequence, cast
import json
from datetime import datetime
import shutil

import yaml


TEMPLATE_DIR = Path("template")
MANIFEST_TEMPLATE_PATH = TEMPLATE_DIR / "manifest.json"
DEPLOY_DIR = Path("deployment")
DEPLOY_NAME_SLUG = "sivad"
STATIC_TEMPLATE_FILES = [
    "icon.png",
    "README.md"
]


@dataclass
class ModInfo:
    name: str
    version: str
    is_enabled: bool
    semver_string: str

    @classmethod
    def format_version(cls, version_dict: dict[str, str]) -> str:
        assert set(version_dict.keys()) == {"major", "minor", "patch"}
        return f"{version_dict.get("major")}.{version_dict.get("minor")}.{version_dict.get("patch")}"

    @classmethod
    def from_dict(cls, yaml_block: dict[str, bool | str | int | float]) -> Self:
        name = yaml_block["name"]
        assert isinstance(name, str)
        version_dict = cast(dict[str, str], yaml_block["versionNumber"])
        version = cls.format_version(version_dict)
        is_enabled = yaml_block["enabled"]
        assert is_enabled is True or is_enabled is False
        return cls(
            name=name,
            version=version,
            is_enabled=is_enabled,
            semver_string=f"{name}-{version}",
        )


def load_yaml(yaml_path: Path) -> Sequence[ModInfo]:
    yaml_string = yaml_path.read_text()
    yaml_data = yaml.load(yaml_string, Loader=yaml.CLoader)
    mods = [ModInfo.from_dict(yaml_block) for yaml_block in yaml_data]
    return [mod for mod in mods if mod.is_enabled]


def load_sources() -> Sequence[ModInfo]:
    mods_yaml_path = Path("sources/mods.yml")
    mods = load_yaml(mods_yaml_path)
    return mods


def copy_template_files(deployment_path: Path) -> None:
    for static_file in STATIC_TEMPLATE_FILES:
        shutil.copy(TEMPLATE_DIR / static_file, deployment_path / static_file)


def init_deployment() -> Path:
    ts = datetime.now()
    ts_string = datetime.strftime(ts, format="%d-%m-%y")
    deploy_name = f"{DEPLOY_NAME_SLUG}_{ts_string}"
    deployment_path = DEPLOY_DIR / deploy_name

    def _refresh(deployment_path: Path) -> None:
        if deployment_path.is_file():
            raise RuntimeError(f"{deployment_path} exists and is not a directory, don't want to break something, exiting...")
        if deployment_path.exists():
            shutil.rmtree(deployment_path)
        deployment_path.mkdir()

    _refresh(deployment_path)
    copy_template_files(deployment_path)
    return deployment_path


@dataclass
class Manifest:
    name: str
    version_number: str
    website_url: str
    description: str
    dependencies: Sequence[str]

    def to_json(self) -> str:
        manifest_dict = {
            "name": self.name,
            "version_number": self.version_number,
            "website_url": self.website_url,
            "description": self.description,
            "dependencies": self.dependencies,
        }
        return json.dumps(manifest_dict)

    def write_to(self, dest: Path) -> None:
        json_string = self.to_json()
        dest.write_text(json_string)

    def with_deps(self, mods: Sequence[ModInfo]) -> Manifest:
        dependencies = [mod.semver_string for mod in mods]
        return Manifest(
            name=self.name,
            version_number=self.version_number,
            website_url=self.website_url,
            description=self.description,
            dependencies=dependencies,
        )

    @classmethod
    def from_template_path(cls, template_path: Path) -> Self:
        json_string = template_path.read_text()
        data = json.loads(json_string)
        name = data["name"]
        version_number = data["version_number"]
        website_url = data["website_url"]
        description = data["description"]
        dependencies = data["dependencies"]
        assert dependencies == []
        return cls(
            name=name,
            version_number=version_number,
            website_url=website_url,
            description=description,
            dependencies=dependencies,
        )


def read_manifest_template() -> Manifest:
    return Manifest.from_template_path(MANIFEST_TEMPLATE_PATH)


def write_manifest_json(mods: Sequence[ModInfo], manifest_path: Path) -> None:
    template_manifest = read_manifest_template()
    manifest = template_manifest.with_deps(mods)
    manifest.write_to(manifest_path)


def populate_dependencies(mods: Sequence[ModInfo], deploy_dir: Path) -> None:
    manifest_path = deploy_dir / "manifest.json"
    write_manifest_json(mods, manifest_path)


def zip_deployment(deploy_dir: Path) -> None:
    zip_name = deploy_dir.name
    zip_path = deploy_dir.parent / zip_name
    shutil.make_archive(zip_path, format="zip", root_dir=deploy_dir)

def deploy_it() -> None:
    mods = load_sources()
    deploy_dir = init_deployment()
    populate_dependencies(mods, deploy_dir)
    zip_deployment(deploy_dir)


if __name__ == "__main__":
    breakpoint()


def test_it():
    deploy_it()
