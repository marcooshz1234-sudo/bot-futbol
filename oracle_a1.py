"""13/11 (Marcos: «reintentar el A1 solo»): crea el servidor gratis de Oracle Cloud (VM.Standard.A1.Flex, 4 OCPU y
24 GB, «Always Free») en cuanto haya hueco en Madrid. Lo lanza GitHub cada 10 min (.github/workflows/oracle_a1.yml).

- Las claves las pone Marcos en los secretos de GitHub (OCI_USER, OCI_TENANCY, OCI_FINGERPRINT, OCI_REGION, OCI_KEY):
  ninguna IA las ve. La clave SSH pública está en oracle/combilocas.pub (la privada solo en el Mac de Marcos).
- Si no hay red de Oracle aún (VCN), la crea: VCN + puerta a internet + subred pública.
- Si Oracle dice «Out of host capacity», no pasa nada: se vuelve a probar a los 10 min.
- Cuando lo consigue: guarda oracle/servidor.json (id e IP), avisa a Marcos al móvil y deja de intentarlo.
- Nunca crea un segundo servidor: si ya hay uno A1 en la cuenta, se para.
"""
import json
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).parent
CARPETA = RAIZ / "oracle"
HECHO = CARPETA / "servidor.json"
PUB = CARPETA / "combilocas.pub"
NOMBRE = "combilocas-bot"
FORMA = "VM.Standard.A1.Flex"
OCPU, MEMORIA, DISCO = 4, 24, 100   # el máximo gratis (Always Free: 4 OCPU, 24 GB, 200 GB de disco en total)
SIN_HUECO = ("out of host capacity", "outofcapacity", "out of capacity")


def huella(pem):
    """El «fingerprint» de la clave de la API sale de la propia clave (MD5 de la pública): no hace falta pedirlo."""
    import hashlib
    from cryptography.hazmat.primitives import serialization
    priv = serialization.load_pem_private_key(pem.encode(), password=None)
    der = priv.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    h = hashlib.md5(der).hexdigest()
    return ":".join(h[i:i + 2] for i in range(0, 32, 2))


def config():
    """Config de OCI, o None si falta la clave (no se hace nada). La clave privada (OCI_KEY) es lo único secreto:
    el usuario y la tenencia son identificadores (van en el workflow) y la huella se calcula de la clave."""
    key = os.environ.get("OCI_KEY")
    c = {"user": os.environ.get("OCI_USER"), "tenancy": os.environ.get("OCI_TENANCY"),
         "region": os.environ.get("OCI_REGION") or "eu-madrid-1", "key_content": key,
         "fingerprint": os.environ.get("OCI_FINGERPRINT") or (huella(key) if key else None)}
    return c if all(c.values()) else None


def es_sin_hueco(e):
    t = f"{getattr(e, 'code', '')} {getattr(e, 'message', '')} {e}".lower()
    return any(s in t for s in SIN_HUECO) or getattr(e, "status", None) == 500 and "capacity" in t


def avisar(texto):
    try:
        from alineaciones_posts import dm   # al privado de Marcos (el dueño del canal)
        dm(texto)
    except Exception as e:
        print(texto, "| aviso no enviado:", e)


def red(oci, cfg, vcn_c, comp):
    """Subred pública donde poner el servidor (la crea si no hay)."""
    for s in vcn_c.list_subnets(comp).data:
        if s.lifecycle_state == "AVAILABLE" and not s.prohibit_public_ip_on_vnic:
            return s.id
    m = oci.core.models
    vcn = vcn_c.create_vcn(m.CreateVcnDetails(compartment_id=comp, cidr_blocks=["10.0.0.0/16"],
                                              display_name="combilocas-vcn", dns_label="combilocas")).data
    oci.wait_until(vcn_c, vcn_c.get_vcn(vcn.id), "lifecycle_state", "AVAILABLE")
    igw = vcn_c.create_internet_gateway(m.CreateInternetGatewayDetails(
        compartment_id=comp, vcn_id=vcn.id, is_enabled=True, display_name="combilocas-igw")).data
    vcn_c.update_route_table(vcn.default_route_table_id, m.UpdateRouteTableDetails(route_rules=[
        m.RouteRule(destination="0.0.0.0/0", destination_type="CIDR_BLOCK", network_entity_id=igw.id)]))
    sub = vcn_c.create_subnet(m.CreateSubnetDetails(compartment_id=comp, vcn_id=vcn.id, cidr_block="10.0.0.0/24",
                                                    display_name="combilocas-subred", dns_label="publica")).data
    oci.wait_until(vcn_c, vcn_c.get_subnet(sub.id), "lifecycle_state", "AVAILABLE")
    print("Red creada:", sub.id)
    return sub.id


def imagen(comp_c, comp):
    """La Ubuntu más nueva para ARM (A1)."""
    imgs = comp_c.list_images(comp, operating_system="Canonical Ubuntu", shape=FORMA,
                              sort_by="TIMECREATED", sort_order="DESC").data
    imgs = [i for i in imgs if "Minimal" not in (i.display_name or "")] or imgs
    return imgs[0].id


def main():
    if HECHO.exists():
        print("El servidor ya está creado:", HECHO.read_text())
        return 0
    cfg = config()
    if not cfg:
        print("Faltan los secretos de Oracle (OCI_*) en GitHub: no se hace nada")
        return 0
    if not PUB.exists():
        print("Falta la clave SSH pública (oracle/combilocas.pub)")
        return 0
    import oci
    comp = cfg["tenancy"]
    comp_c = oci.core.ComputeClient(cfg)
    vcn_c = oci.core.VirtualNetworkClient(cfg)
    iam = oci.identity.IdentityClient(cfg)
    for i in comp_c.list_instances(comp).data:   # nunca dos
        if i.shape == FORMA and i.lifecycle_state not in ("TERMINATED", "TERMINATING"):
            print("Ya hay un A1 en la cuenta:", i.id, i.lifecycle_state)
            return guardar(oci, cfg, comp_c, vcn_c, comp, i)
    sub = red(oci, cfg, vcn_c, comp)
    img = imagen(comp_c, comp)
    m = oci.core.models
    for ad in iam.list_availability_domains(comp).data:
        det = m.LaunchInstanceDetails(
            compartment_id=comp, availability_domain=ad.name, shape=FORMA, display_name=NOMBRE,
            shape_config=m.LaunchInstanceShapeConfigDetails(ocpus=OCPU, memory_in_gbs=MEMORIA),
            source_details=m.InstanceSourceViaImageDetails(image_id=img, boot_volume_size_in_gbs=DISCO),
            create_vnic_details=m.CreateVnicDetails(subnet_id=sub, assign_public_ip=True),
            metadata={"ssh_authorized_keys": PUB.read_text().strip()})
        try:
            ins = comp_c.launch_instance(det).data
        except oci.exceptions.ServiceError as e:
            if es_sin_hueco(e):
                print(f"Sin hueco en {ad.name}: se vuelve a probar en 10 min")
                continue
            if e.status == 429:
                print("Oracle pide ir más despacio (429): siguiente vuelta")
                return 0
            raise
        print("¡Creado!", ins.id)
        return guardar(oci, cfg, comp_c, vcn_c, comp, ins)
    return 0


def guardar(oci, cfg, comp_c, vcn_c, comp, ins):
    ins = oci.wait_until(comp_c, comp_c.get_instance(ins.id), "lifecycle_state", "RUNNING", max_wait_seconds=900).data
    ip = None
    for v in comp_c.list_vnic_attachments(comp, instance_id=ins.id).data:
        ip = vcn_c.get_vnic(v.vnic_id).data.public_ip or ip
    CARPETA.mkdir(exist_ok=True)
    HECHO.write_text(json.dumps({"id": ins.id, "ip": ip, "forma": FORMA, "ocpu": OCPU, "memoria_gb": MEMORIA,
                                 "creado": str(ins.time_created)}, indent=2) + "\n")
    avisar(f"🎉 ¡Servidor gratis de Oracle creado! (A1, {OCPU} núcleos y {MEMORIA} GB)\nIP: {ip}\n"
           "Dile a Claude que siga con la mudanza del bot.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
