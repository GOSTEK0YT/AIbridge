"""Build the installable Roblox Studio plugin from the Luau source."""

from pathlib import Path
import uuid


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "AIBridgePlugin.server.lua"
OUTPUT = ROOT / "release" / "AI-Bridge-Cloud.rbxmx"


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    if "]]>" in source:
        raise ValueError("Plugin source cannot contain a CDATA terminator")
    guid = str(uuid.uuid5(uuid.NAMESPACE_URL, "https://ai-bridge-cloud.onrender.com/plugin"))
    xml = f'''<roblox xmlns:xmime="http://www.w3.org/2005/05/xmlmime" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://www.roblox.com/roblox.xsd" version="4">
  <External>null</External>
  <External>nil</External>
  <Item class="Script" referent="RBXAI_BRIDGE_CLOUD">
    <Properties>
      <ProtectedString name="Source"><![CDATA[{source}]]></ProtectedString>
      <bool name="Disabled">false</bool>
      <Content name="LinkedSource"><null></null></Content>
      <token name="RunContext">0</token>
      <string name="ScriptGuid">{{{guid}}}</string>
      <BinaryString name="AttributesSerialize"></BinaryString>
      <SecurityCapabilities name="Capabilities">0</SecurityCapabilities>
      <bool name="DefinesCapabilities">false</bool>
      <string name="Name">AI Bridge</string>
      <int64 name="SourceAssetId">-1</int64>
      <BinaryString name="Tags"></BinaryString>
    </Properties>
  </Item>
</roblox>
'''
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(xml, encoding="utf-8", newline="\n")
    print(OUTPUT)


if __name__ == "__main__":
    main()
