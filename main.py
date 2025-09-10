import json
import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Load resolutions
with open("resolutions.json", "r", encoding="utf-8") as f:
    resolutions = json.load(f)

def get_resolution(case_number: str):
    return next((r for r in resolutions if r["caseNumber"] == case_number), None)

def list_latest(limit=10):
    sorted_res = sorted(resolutions, key=lambda r: r.get("date", ""), reverse=True)
    return sorted_res[:limit]

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)

print("bot starting")

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        # Global sync (works everywhere, but first time can take ~1h to propagate)
        synced = await bot.tree.sync()
        print(f"📌 Synced {len(synced)} command(s).")
    except Exception as e:
        print("Sync failed:", e)

@bot.tree.command(name="resolution", description="Get resolution by case number")
@app_commands.describe(case_number="The case number of the resolution")
async def resolution(interaction: discord.Interaction, case_number: str):
    res = get_resolution(case_number)
    if res:
        embed = discord.Embed(
            title=res.get("title") or f"Case {res['caseNumber']}",
            description=res.get("preamble", "—"),
            color=0x2b2d31
        )
        embed.add_field(name="Case Number", value=res["caseNumber"], inline=True)
        embed.add_field(name="Type", value=res.get("type", "—"), inline=True)
        embed.add_field(name="Submitted By", value=res.get("submittedBy", "—"), inline=True)
        embed.add_field(name="Date", value=res.get("date", "—"), inline=True)
        embed.add_field(name="Signatories", value=", ".join(res.get("signatories", [])) or "—", inline=False)

        clauses = res.get("operativeClauses", [])
        conclusion = res.get("conclusion", "—")

        text = "\n".join([f"{i+1}. {c}" for i, c in enumerate(clauses)]) + f"\n\n**Conclusion**\n{conclusion}"
        if len(text) > 1024:
            chunks = [text[i:i+1024] for i in range(0, len(text), 1024)]
            for i, chunk in enumerate(chunks):
                embed.add_field(name="Operative Clauses" if i == 0 else "Continued", value=chunk, inline=False)
        else:
            embed.add_field(name="Operative Clauses", value=text, inline=False)

        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"No resolution found for case number {case_number}.", ephemeral=True)


# /reloadresolutions command for admins
@bot.tree.command(name="reloadresolutions", description="Reload resolutions from the JSON file")
@app_commands.checks.has_permissions(administrator=True)
async def reload_resolutions(interaction: discord.Interaction):
    global resolutions
    try:
        with open("resolutions.json", "r", encoding="utf-8") as f:
            resolutions = json.load(f)
        await interaction.response.send_message("Resolutions reloaded successfully.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Failed to reload resolutions: {e}", ephemeral=True)



# /createresolution <case_num> <clause1> <clause2> ... command for admins
@bot.tree.command(name="createresolution", description="Create a new resolution")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    case_number="The case number of the resolution",
    title="The title of the resolution",
    preamble="The preamble of the resolution",
    type="The type of the resolution",
    submitted_by="Who submitted the resolution",
    date="The date of the resolution (YYYY-MM-DD)",
    signatories="Comma-separated list of signatories",
    clauses="Comma-separated list of operative clauses",
    conclusion="The conclusion of the resolution"
)
async def create_resolution(
    interaction: discord.Interaction,
    case_number: str,
    title: str,
    preamble: str,
    type: str,
    submitted_by: str,
    date: str,
    signatories: str,
    clauses: str,
    conclusion: str
):
    global resolutions
    if get_resolution(case_number):
        await interaction.response.send_message(f"A resolution with case number {case_number} already exists.", ephemeral=True)
        return

    new_res = {
        "caseNumber": case_number,
        "title": title,
        "preamble": preamble,
        "type": type,
        "submittedBy": submitted_by,
        "date": date,
        "signatories": [s.strip() for s in signatories.split(",")],
        "operativeClauses": [c.strip() for c in clauses.split(",")],
        "conclusion": conclusion
    }
    resolutions.append(new_res)

    try:
        with open("resolutions.json", "w", encoding="utf-8") as f:
            json.dump(resolutions, f, ensure_ascii=False, indent=4)
        await interaction.response.send_message(f"Resolution {case_number} created successfully.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Failed to save the new resolution: {e}", ephemeral=True)


bot.run(TOKEN)