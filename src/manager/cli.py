#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
from typing import Optional

from .metadata import MetadataManager, DataSource
from .version_manager import VersionManager, VersionChangeType
from .stats import StatsManager
from .exporter import Exporter, ExportFormat


def main():
    parser = argparse.ArgumentParser(
        description="Data Management & Version Control CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan data directory
  python -m src.manager.cli scan
  
  # List all datasets
  python -m src.manager.cli list
  
  # Show stats for all datasets
  python -m src.manager.cli stats
  
  # Show stats for a specific dataset
  python -m src.manager.cli stats --dataset <dataset_id>
  
  # Import data
  python -m src.manager.cli import --input <path> --source raw
  
  # Export dataset
  python -m src.manager.cli export --dataset <dataset_id> --output <path> --format jsonl
  
  # Create new version
  python -m src.manager.cli version --dataset <dataset_id> --type patch --description "Updated data"
  
  # List versions
  python -m src.manager.cli versions --dataset <dataset_id>
        """
    )

    subparsers = parser.add_subparsers(title="Commands", dest="command", help="Available commands")

    # Scan command
    scan_parser = subparsers.add_parser("scan", help="Scan data directory for new datasets")
    scan_parser.add_argument("--data-dir", default="/workspace/data", help="Data directory path")

    # List command
    list_parser = subparsers.add_parser("list", help="List all datasets")
    list_parser.add_argument("--source", choices=["raw", "annotated", "final"], help="Filter by source")
    list_parser.add_argument("--data-dir", default="/workspace/data", help="Data directory path")

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show statistics")
    stats_parser.add_argument("--dataset", help="Dataset ID (optional, show overall stats if not specified)")
    stats_parser.add_argument("--data-dir", default="/workspace/data", help="Data directory path")

    # Import command
    import_parser = subparsers.add_parser("import", help="Import data")
    import_parser.add_argument("--input", required=True, help="Input file or directory path")
    import_parser.add_argument("--name", help="Dataset name")
    import_parser.add_argument("--source", choices=["raw", "annotated", "final"], default="raw", help="Source type")
    import_parser.add_argument("--data-dir", default="/workspace/data", help="Data directory path")

    # Export command
    export_parser = subparsers.add_parser("export", help="Export dataset")
    export_parser.add_argument("--dataset", required=True, help="Dataset ID")
    export_parser.add_argument("--output", required=True, help="Output path")
    export_parser.add_argument("--format", choices=["jsonl", "json", "csv", "zip"], default="jsonl", help="Export format")
    export_parser.add_argument("--no-metadata", action="store_true", help="Don't include metadata")
    export_parser.add_argument("--version", help="Specific version to export")
    export_parser.add_argument("--data-dir", default="/workspace/data", help="Data directory path")

    # Version command
    version_parser = subparsers.add_parser("version", help="Create new dataset version")
    version_parser.add_argument("--dataset", required=True, help="Dataset ID")
    version_parser.add_argument("--type", choices=["major", "minor", "patch"], default="patch", help="Version change type")
    version_parser.add_argument("--description", help="Version description")
    version_parser.add_argument("--author", help="Author name")
    version_parser.add_argument("--data-dir", default="/workspace/data", help="Data directory path")

    # Versions command
    versions_parser = subparsers.add_parser("versions", help="List dataset versions")
    versions_parser.add_argument("--dataset", required=True, help="Dataset ID")
    versions_parser.add_argument("--data-dir", default="/workspace/data", help="Data directory path")

    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore dataset version")
    restore_parser.add_argument("--dataset", required=True, help="Dataset ID")
    restore_parser.add_argument("--version", required=True, help="Version to restore")
    restore_parser.add_argument("--output", required=True, help="Output path")
    restore_parser.add_argument("--data-dir", default="/workspace/data", help="Data directory path")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # Execute command
    if args.command == "scan":
        handle_scan(args)
    elif args.command == "list":
        handle_list(args)
    elif args.command == "stats":
        handle_stats(args)
    elif args.command == "import":
        handle_import(args)
    elif args.command == "export":
        handle_export(args)
    elif args.command == "version":
        handle_version(args)
    elif args.command == "versions":
        handle_versions(args)
    elif args.command == "restore":
        handle_restore(args)


def handle_scan(args):
    metadata_manager = MetadataManager(args.data_dir)
    new_datasets = metadata_manager.scan_data_directory()
    print(f"Scanned data directory. Found {len(new_datasets)} new dataset(s):")
    for dataset in new_datasets:
        print(f"  - {dataset.dataset_id}: {dataset.name} ({dataset.data_count} entries)")


def handle_list(args):
    metadata_manager = MetadataManager(args.data_dir)
    source = DataSource(args.source) if args.source else None
    datasets = metadata_manager.list_datasets(source)
    print(f"Found {len(datasets)} dataset(s):")
    for dataset in datasets:
        size = format_size(dataset.file_size)
        print(f"  {dataset.dataset_id}")
        print(f"    Name: {dataset.name}")
        print(f"    Source: {dataset.source.value}")
        print(f"    Entries: {dataset.data_count}")
        print(f"    Size: {size}")
        print(f"    Version: {dataset.version}")
        print()


def handle_stats(args):
    stats_manager = StatsManager(args.data_dir)
    stats_manager.print_stats_report(args.dataset)


def handle_import(args):
    exporter = Exporter(args.data_dir)
    source = DataSource(args.source)
    result = exporter.import_data(args.input, args.name, source)
    if result.success:
        print(f"Successfully imported {result.imported_count} entries!")
        if result.warnings:
            print("Warnings:")
            for warning in result.warnings:
                print(f"  - {warning}")
    else:
        print("Import failed:")
        for error in result.errors:
            print(f"  - {error}")
        sys.exit(1)


def handle_export(args):
    exporter = Exporter(args.data_dir)
    format = ExportFormat(args.format)
    try:
        output_path = exporter.export_dataset(
            args.dataset,
            args.output,
            format,
            not args.no_metadata,
            args.version
        )
        print(f"Successfully exported to: {output_path}")
    except Exception as e:
        print(f"Export failed: {str(e)}")
        sys.exit(1)


def handle_version(args):
    version_manager = VersionManager(args.data_dir)
    change_type = VersionChangeType(args.type)
    try:
        dataset_version = version_manager.create_new_version(
            args.dataset,
            None,
            change_type,
            args.description,
            args.author
        )
        print(f"Created new version: {dataset_version.current_version}")
    except Exception as e:
        print(f"Failed to create version: {str(e)}")
        sys.exit(1)


def handle_versions(args):
    version_manager = VersionManager(args.data_dir)
    versions = version_manager.list_versions(args.dataset)
    if not versions:
        print(f"No versions found for dataset: {args.dataset}")
        return
    print(f"Versions for dataset {args.dataset}:")
    for v in versions:
        print(f"  {v.version}")
        print(f"    Created: {v.timestamp}")
        print(f"    Type: {v.change_type.value}")
        if v.description:
            print(f"    Description: {v.description}")
        if v.author:
            print(f"    Author: {v.author}")
        print(f"    Entries: {v.data_count}")
        print()


def handle_restore(args):
    version_manager = VersionManager(args.data_dir)
    restored_path = version_manager.restore_version(args.dataset, args.version, args.output)
    if restored_path:
        print(f"Successfully restored version {args.version} to: {restored_path}")
    else:
        print(f"Failed to restore version {args.version}")
        sys.exit(1)


def format_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


if __name__ == "__main__":
    main()
