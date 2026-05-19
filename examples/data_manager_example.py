#!/usr/bin/env python3
"""
Data Management & Version Control - Usage Examples

This file demonstrates how to use the data management and version control
modules to manage datasets, track versions, calculate statistics, and export/import data.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.manager import (
    DataSource,
    MetadataManager,
    VersionManager,
    VersionChangeType,
    StatsManager,
    Exporter,
    ExportFormat,
)


def example_metadata_management():
    """Demonstrate metadata management functionality."""
    print("=" * 60)
    print("Example 1: Metadata Management")
    print("=" * 60)

    # Initialize metadata manager
    metadata_manager = MetadataManager("/workspace/data")

    # Scan data directory for existing datasets
    print("\n1. Scanning data directory...")
    new_datasets = metadata_manager.scan_data_directory()
    print(f"   Found {len(new_datasets)} new dataset(s)")

    # List all datasets
    print("\n2. Listing all datasets...")
    all_datasets = metadata_manager.list_datasets()
    for dataset in all_datasets:
        print(f"   - {dataset.dataset_id}: {dataset.name} ({dataset.data_count} entries)")

    return all_datasets


def example_version_control(dataset_id: str, dataset_path: Path):
    """Demonstrate version control functionality."""
    print("\n" + "=" * 60)
    print("Example 2: Version Control")
    print("=" * 60)

    # Initialize version manager
    version_manager = VersionManager("/workspace/data")

    # Create initial version
    print("\n1. Creating initial version...")
    version = version_manager.create_initial_version(
        dataset_id=dataset_id,
        file_or_dir_path=dataset_path,
        description="Initial dataset version",
        author="Example User"
    )
    print(f"   Created version: {version.current_version}")

    # List all versions
    print("\n2. Listing all versions...")
    versions = version_manager.list_versions(dataset_id)
    for v in versions:
        print(f"   - {v.version} ({v.timestamp}): {v.description or 'No description'}")

    # Create a new patch version
    print("\n3. Creating new patch version...")
    new_version = version_manager.create_new_version(
        dataset_id=dataset_id,
        file_or_dir_path=dataset_path,
        change_type=VersionChangeType.PATCH,
        description="Updated dataset with minor changes",
        author="Example User"
    )
    print(f"   Created version: {new_version.current_version}")

    return version_manager


def example_statistics(dataset_id: str):
    """Demonstrate statistics functionality."""
    print("\n" + "=" * 60)
    print("Example 3: Statistics & Analysis")
    print("=" * 60)

    # Initialize stats manager
    stats_manager = StatsManager("/workspace/data")

    # Get overall stats
    print("\n1. Overall statistics:")
    overall = stats_manager.get_overall_stats()
    print(f"   - Total datasets: {overall.total_datasets}")
    print(f"   - Total entries: {overall.total_entries}")
    print(f"   - Source distribution: {overall.source_distribution}")

    # Analyze a specific dataset
    if dataset_id:
        metadata_manager = MetadataManager("/workspace/data")
        dataset = metadata_manager.load_metadata(dataset_id)
        if dataset:
            print(f"\n2. Analyzing dataset: {dataset.name}")
            stats = stats_manager.analyze_dataset(dataset)
            print(f"   - Total entries: {stats.total_entries}")
            print(f"   - Average quality score: {stats.quality_stats.avg_quality_score:.2f}")
            print(f"   - Verified entries: {stats.quality_stats.verified_count}")
            print(f"   - Total annotations: {stats.annotation_stats.total_annotations}")


def example_export_import(dataset_id: str):
    """Demonstrate export/import functionality."""
    print("\n" + "=" * 60)
    print("Example 4: Export & Import")
    print("=" * 60)

    # Initialize exporter
    exporter = Exporter("/workspace/data")

    # Export dataset in different formats
    print("\n1. Exporting dataset to JSONL...")
    output_jsonl = Path("/tmp/exported_dataset.jsonl")
    output_path = exporter.export_dataset(
        dataset_id=dataset_id,
        output_path=output_jsonl,
        format=ExportFormat.JSONL,
        include_metadata=True
    )
    print(f"   Exported to: {output_path}")

    print("\n2. Exporting dataset to ZIP...")
    output_zip = Path("/tmp/exported_dataset.zip")
    output_path = exporter.export_dataset(
        dataset_id=dataset_id,
        output_path=output_zip,
        format=ExportFormat.ZIP,
        include_metadata=True
    )
    print(f"   Exported to: {output_path}")

    # Clean up exported files
    if output_jsonl.exists():
        output_jsonl.unlink()
    meta_jsonl = Path("/tmp/exported_dataset_metadata.json")
    if meta_jsonl.exists():
        meta_jsonl.unlink()
    if output_zip.exists():
        output_zip.unlink()


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("Data Management & Version Control - Examples")
    print("=" * 60)

    # Example 1: Metadata Management
    datasets = example_metadata_management()

    if datasets:
        # Use first dataset for other examples
        first_dataset = datasets[0]
        dataset_id = first_dataset.dataset_id
        dataset_path = first_dataset.file_path

        # Example 2: Version Control
        example_version_control(dataset_id, dataset_path)

        # Example 3: Statistics
        example_statistics(dataset_id)

        # Example 4: Export/Import
        example_export_import(dataset_id)
    else:
        print("\nNo datasets found. Please make sure you have data in /workspace/data directory.")
        print("\nYou can try running the following commands first:")
        print("  python -m src.manager.cli scan")
        print("  python -m src.manager.cli list")

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)
    print("\nFor CLI usage examples, run:")
    print("  python -m src.manager.cli --help")


if __name__ == "__main__":
    main()
