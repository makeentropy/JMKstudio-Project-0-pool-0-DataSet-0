"""
BaseXOR 探针终端 CLI

命令总览：
  basexor ca init       初始化证书服务器（CA）并签发探针代码签名凭据
  basexor block sign    用 CA 凭据签名分布式区块链数据块，输出 BaseXOR 清单信封
  basexor block verify  校验数据块清单的 CA 签名/证书链/有效期，输出合规判定
  basexor matrix        批量校验数据块清单，生成合法合规矩阵
  basexor apt line      输出 APT 联络线（apt 源条目 + 安装指令）
  basexor apt pack      将探针打包为 .deb（APT 联络线分发产物）

入口：
  - ai-crawler  (pyproject: ai_llm_agent_crawler.cli:main) 默认进入 basexor
  - basexor     (pyproject: ai_llm_agent_crawler.cli:basexor_main)
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

import click
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography import x509
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ai_llm_agent_crawler.security.basexor import (
    APTContactLine,
    BaseXORProbe,
    CodeSigningCredential,
    ComplianceCheck,
    ComplianceVerdict,
    decode_manifest_envelope,
    encode_manifest_envelope,
    build_deb_package,
)
from ai_llm_agent_crawler.security.ca_system import CertificateAuthority
from ai_llm_agent_crawler.security.datachain_compression import DataBlock

console = Console()

# 合规判定的颜色映射
_VERDICT_STYLE = {
    ComplianceVerdict.COMPLIANT: "green",
    ComplianceVerdict.NONCOMPLIANT: "red",
    ComplianceVerdict.UNKNOWN: "yellow",
}


# ---------------------------------------------------------------------------
# CA 状态读写
# ---------------------------------------------------------------------------


def _write_ca_state(ca_dir: Path, ca: CertificateAuthority, credential: CodeSigningCredential) -> None:
    """将 CA 证书/私钥与代码签名凭据写入目录"""
    ca_dir.mkdir(parents=True, exist_ok=True)

    ca_cert_pem = ca.export_ca_certificate("PEM")
    ca_key_pem = ca.export_ca_private_key(password=None)

    ca_cert_path = ca_dir / "ca_cert.pem"
    ca_key_path = ca_dir / "ca_key.pem"
    cred_path = ca_dir / "credential.json"

    ca_cert_path.write_bytes(ca_cert_pem)
    ca_key_path.write_bytes(ca_key_pem)
    os.chmod(ca_key_path, 0o600)

    cred_path.write_text(
        json.dumps(credential.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.chmod(cred_path, 0o600)


def _load_credential(ca_dir: Path) -> CodeSigningCredential:
    """从目录加载代码签名凭据"""
    cred_path = ca_dir / "credential.json"
    if not cred_path.exists():
        raise click.ClickException(f"未找到代码签名凭据: {cred_path}（请先 basexor ca init）")
    data = json.loads(cred_path.read_text(encoding="utf-8"))
    return CodeSigningCredential.from_dict(data)


def _load_ca_certificate(ca_dir: Path) -> x509.Certificate:
    """从目录加载 CA 证书"""
    ca_cert_path = ca_dir / "ca_cert.pem"
    if not ca_cert_path.exists():
        raise click.ClickException(f"未找到 CA 证书: {ca_cert_path}")
    return x509.load_pem_x509_certificate(ca_cert_path.read_bytes(), default_backend())


# ---------------------------------------------------------------------------
# 顶层命令组
# ---------------------------------------------------------------------------


@click.group(help="BaseXOR 探针 - 分布式区块链数据块 CA 校验终端 CLI")
def basexor() -> None:
    """BaseXOR 探针命令组"""


# ---- ca ----


@basexor.group(help="证书服务器（CA）管理")
def ca() -> None:
    """CA 管理"""


@ca.command("init", help="初始化 CA 并签发探针代码签名凭据")
@click.option("--ca-dir", required=True, type=click.Path(file_okay=False), help="CA 状态目录")
@click.option("--name", default="BaseXOR CA", help="CA 名称")
@click.option("--key-size", default=4096, type=int, help="RSA 密钥大小")
@click.option("--validity-days", default=3650, type=int, help="根证书有效期（天）")
def ca_init(ca_dir: str, name: str, key_size: int, validity_days: int) -> None:
    ca_obj = CertificateAuthority(name=name, key_size=key_size, validity_days=validity_days)
    ca_obj.initialize()
    credential = CodeSigningCredential.issue(ca_obj, common_name="basexor-probe")

    ca_path = Path(ca_dir)
    _write_ca_state(ca_path, ca_obj, credential)

    ca_cert = ca_obj.export_ca_certificate("PEM").decode("ascii")
    fingerprint = ca_obj._certificate_info.public_key_fingerprint if ca_obj._certificate_info else ""

    console.print(Panel.fit(
        f"[bold green]CA 初始化完成[/]\n"
        f"名称: {name}\n"
        f"目录: {ca_path}\n"
        f"证书指纹: {fingerprint}\n"
        f"已签发代码签名凭据: {ca_path / 'credential.json'}\n"
        f"[yellow]注意: ca_key.pem 为明文 PEM，请妥善保管（生产环境应加密）[/]",
        title="BaseXOR 证书服务器",
    ))


# ---- block ----


@basexor.group(help="分布式区块链数据块签名/校验")
def block() -> None:
    """数据块操作"""


@block.command("sign", help="签名数据块，输出 BaseXOR 清单信封")
@click.option("--ca-dir", required=True, type=click.Path(file_okay=False), help="CA 状态目录")
@click.option("--data", required=True, type=click.Path(exists=True, dir_okay=False), help="数据块文件")
@click.option("--block-id", required=True, help="数据块 ID")
@click.option("--seq", required=True, type=int, help="数据块序号")
@click.option("--out", type=click.Path(dir_okay=False), default="-", help="输出清单文件（默认 stdout）")
def block_sign(ca_dir: str, data: str, block_id: str, seq: int, out: str) -> None:
    credential = _load_credential(Path(ca_dir))
    probe = BaseXORProbe(credential=credential)

    block = DataBlock(block_id=block_id, data=Path(data).read_bytes(), sequence_number=seq)
    manifest = probe.sign_block(block)
    envelope = encode_manifest_envelope(manifest)

    payload = json.dumps(envelope, ensure_ascii=False, indent=2)
    if out == "-":
        console.print_json(payload)
    else:
        Path(out).write_text(payload, encoding="utf-8")
        console.print(f"[green]已写入清单信封:[/] {out}")


@block.command("verify", help="校验数据块清单")
@click.option("--data", required=True, type=click.Path(exists=True, dir_okay=False), help="数据块文件")
@click.option("--manifest", required=True, type=click.Path(exists=True, dir_okay=False), help="清单信封文件")
def block_verify(data: str, manifest: str) -> None:
    envelope = json.loads(Path(manifest).read_text(encoding="utf-8"))
    try:
        m = decode_manifest_envelope(envelope)
    except ValueError as exc:
        raise click.ClickException(f"清单解码失败: {exc}")

    block_data = Path(data).read_bytes()
    probe = BaseXORProbe()  # 仅校验模式：不提供 CA，吊销状态将为"待核验"
    items = probe.verify_manifest(m, block_data=block_data)

    table = Table(title=f"BaseXOR 数据块校验 - {m.block_id}")
    table.add_column("检查项", style="cyan")
    table.add_column("判定")
    table.add_column("说明", overflow="fold")
    for it in items:
        table.add_row(it.check.label_cn, it.verdict.label_cn, it.detail)
    console.print(table)

    noncompliant = any(i.verdict == ComplianceVerdict.NONCOMPLIANT for i in items)
    unknown = any(i.verdict == ComplianceVerdict.UNKNOWN for i in items)
    if noncompliant:
        overall = ComplianceVerdict.NONCOMPLIANT
    elif unknown:
        overall = ComplianceVerdict.UNKNOWN
    else:
        overall = ComplianceVerdict.COMPLIANT
    console.print(f"总体判定: [{_VERDICT_STYLE[overall]}]{overall.label_cn}[/]")
    if overall == ComplianceVerdict.NONCOMPLIANT:
        sys.exit(1)


# ---- matrix ----


@basexor.command("matrix", help="批量校验数据块清单，生成合法合规矩阵")
@click.option("--manifests-dir", required=True, type=click.Path(exists=True, file_okay=False), help="清单信封目录")
@click.option("--blocks-dir", type=click.Path(exists=True, file_okay=False), default=None, help="数据块目录（<block_id>.bin）")
@click.option("--json", "as_json", is_flag=True, help="以 JSON 输出矩阵")
def matrix(manifests_dir: str, blocks_dir: Optional[str], as_json: bool) -> None:
    mdir = Path(manifests_dir)
    envelopes = sorted(mdir.glob("*.json"))
    if not envelopes:
        raise click.ClickException(f"目录中未找到清单信封: {mdir}")

    manifests = []
    for env_file in envelopes:
        envelope = json.loads(env_file.read_text(encoding="utf-8"))
        try:
            manifests.append(decode_manifest_envelope(envelope))
        except ValueError as exc:
            raise click.ClickException(f"{env_file.name}: 清单解码失败: {exc}")

    blocks = {}
    if blocks_dir:
        for m in manifests:
            candidate = Path(blocks_dir) / f"{m.block_id}.bin"
            if candidate.exists():
                blocks[m.block_id] = DataBlock(
                    block_id=m.block_id, data=candidate.read_bytes(), sequence_number=m.sequence_number
                )

    probe = BaseXORProbe()
    result = probe.verify_blocks(manifests, blocks=blocks)

    if as_json:
        console.print_json(json.dumps(result.to_dict(), ensure_ascii=False))
    else:
        table = Table(title="BaseXOR 合法合规矩阵", show_lines=True)
        table.add_column("数据块 ID", style="cyan")
        for check in ComplianceCheck:
            table.add_column(check.label_cn)
        table.add_column("总体", style="bold")

        for row in result.to_table_rows():
            cells = [row["block_id"]]
            for check in ComplianceCheck:
                v = row[check.value]
                style = {
                    ComplianceVerdict.COMPLIANT.value: "green",
                    ComplianceVerdict.NONCOMPLIANT.value: "red",
                    ComplianceVerdict.UNKNOWN.value: "yellow",
                }.get(v, "white")
                cells.append(f"[{style}]{v}[/]")
            overall_v = row["verdict"]
            overall_style = {
                "合规": "green",
                "不合规": "red",
                "待核验": "yellow",
            }.get(overall_v, "white")
            cells.append(f"[{overall_style}]{overall_v}[/]")
            table.add_row(*cells)
        console.print(table)

        overall = result.overall_verdict()
        console.print(
            f"\nCA: {result.ca_subject or '(未知)'}  |  "
            f"探针: {result.probe_id}  |  "
            f"整体判定: [{_VERDICT_STYLE[overall]}]{overall.label_cn}[/]"
        )

    if result.overall_verdict() == ComplianceVerdict.NONCOMPLIANT:
        sys.exit(1)


# ---- apt ----


@basexor.group(help="APT 联络线（向 Aliyun 云 Kali Linux 主机分发探针）")
def apt() -> None:
    """APT 联络线"""


@apt.command("line", help="输出 APT 联络线配置")
@click.option("--repo-url", default=APTContactLine().repo_url, help="apt 仓库 URL")
@click.option("--distribution", default=APTContactLine().distribution, help="发行版")
@click.option("--component", default=APTContactLine().component, help="组件")
@click.option("--install", is_flag=True, help="同时输出 Kali 主机安装指令")
def apt_line(repo_url: str, distribution: str, component: str, install: bool) -> None:
    contact = APTContactLine(
        repo_url=repo_url, distribution=distribution, component=component
    )
    console.print(Panel.fit(contact.sources_entry().strip(), title="apt sources.list.d 条目"))
    console.print(f"keyring: {contact.keyring_path}")
    console.print(f"文件: {contact.sources_dir}/{contact.sources_filename}")
    if install:
        console.print(Panel.fit(contact.install_instructions(), title="Kali 主机启用联络线"))


@apt.command("pack", help="将探针打包为 .deb")
@click.option("--staging-dir", required=True, type=click.Path(file_okay=False), help="暂存目录")
@click.option("--output-dir", required=True, type=click.Path(file_okay=False), help=".deb 输出目录")
@click.option("--version", default="0.1.0", help="包版本")
@click.option("--no-dpkg", is_flag=True, help="仅暂存目录，不调用 dpkg-deb")
def apt_pack(staging_dir: str, output_dir: str, version: str, no_dpkg: bool) -> None:
    deb_path = build_deb_package(
        staging_dir=staging_dir,
        output_dir=output_dir,
        version=version,
        run_dpkg=not no_dpkg,
    )
    if deb_path is not None:
        console.print(f"[green]已构建 .deb:[/] {deb_path}")
    else:
        console.print(
            f"[yellow]仅暂存 Debian 包目录（未构建 .deb）[/]\n"
            f"暂存位置: {Path(staging_dir) / 'basexor-probe'}\n"
            f"提示: 在 Aliyun 云 Kali Linux 主机上运行此命令时，dpkg-deb 可用即可自动构建。"
        )


# ---------------------------------------------------------------------------
# 控制台入口
# ---------------------------------------------------------------------------


def basexor_main() -> None:
    """basexor 控制台入口"""
    basexor()


def main() -> None:
    """ai-crawler 控制台入口（默认进入 BaseXOR 探针）"""
    basexor()


if __name__ == "__main__":
    basexor()
