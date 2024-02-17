import disnake
from disnake.ext import commands, tasks
import re
from datetime import datetime, timedelta
from config import TOKEN, EMOJI_UPVOTE, EMOJI_DOWNVOTE, SUPPORTED_DOMAINS

intents = disnake.Intents.all()
bot = commands.Bot(intents=intents)

# Store the channel ID in a variable, initially None
target_channel_id = None

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')

@bot.slash_command(description="Set the target channel for message tracking")
async def set_channel(inter, channel: disnake.TextChannel):
    global target_channel_id
    target_channel_id = channel.id
    await inter.response.send_message(f"Target channel set to: {channel.name}")

@bot.slash_command(description="Reset the target channel for message tracking")
async def reset_channel(inter):
    global target_channel_id
    target_channel_id = None
    await inter.response.send_message("Target channel has been reset.")

@bot.slash_command(description="Announce the clip of the day")
async def announce_clip(inter):
    if not target_channel_id:
        await inter.response.send_message("No target channel set. Use /set_channel to set one.")
        return

    channel = bot.get_channel(target_channel_id)
    if not channel:
        await inter.response.send_message("Channel not found.")
        return

    await inter.response.defer()  # Use defer for longer operations

    top_clip, top_score, top_author = await get_top_voted_clip(channel)

    if top_clip:
        # Create an embed for the announcement
        embed = disnake.Embed(
            title="🎉 Clip of the Day 🎉",
            color=0xFFD700,  # Gold color
            description=f"Congratulations to {top_author.mention} for today's top clip!\n\n**Clip:** {top_clip}\n**Score:** {top_score} votes!\n\nKeep sharing your amazing clips and voting for your favorites! 🌟"
        )
        await inter.edit_original_message(embed=embed)
    else:
        await inter.edit_original_message(content="No clips found or no votes tallied.")

async def get_top_voted_clip(channel):
    one_week_ago = datetime.utcnow() - timedelta(weeks=1)
    top_clip = None
    top_score = -float('inf')  # Start with the lowest possible score
    top_author = None

    async for message in channel.history(limit=100, after=one_week_ago):
        upvotes = 0
        downvotes = 0
        for reaction in message.reactions:
            if str(reaction.emoji) == '👍':
                upvotes = reaction.count - 1  # Subtract 1 to ignore the bot's own reaction
            elif str(reaction.emoji) == '👎':
                downvotes = reaction.count - 1

        net_score = upvotes - downvotes
        if net_score > top_score:
            top_score = net_score
            top_clip = message.content
            top_author = message.author

    return top_clip, top_score, top_author

@bot.slash_command(description="Manually clear reactions from messages older than a week in the target channel")
async def clear_reactions(inter):
    if not target_channel_id:
        await inter.response.send_message("No target channel set. Use /set_channel to set one.")
        return
    await inter.response.send_message("Clearing reactions...")
    await clear_old_reactions_now()

async def clear_old_reactions_now():
    if target_channel_id is None:
        print("No target channel set.")
        return
    
    channel = bot.get_channel(target_channel_id)
    one_week_ago = datetime.utcnow() - timedelta(weeks=1)
    cleared_count = 0
    
    async for message in channel.history(limit=None, after=one_week_ago):
        if message.created_at < one_week_ago:
            try:
                await message.clear_reactions()
                cleared_count += 1
            except Exception as e:
                print(f"Error clearing reactions: {e}")
    
    print(f"Cleared reactions from {cleared_count} messages.")

@bot.event
async def on_message(message):
    # Ignore messages sent by the bot itself or without a guild (private messages)
    if message.author == bot.user or not message.guild:
        return

    # Check if the message contains a supported clip link
    if target_channel_id and message.channel.id == target_channel_id:
        clip_url_pattern = r'https?://[\w.-]+/\S+\.mp4'
        if any(domain in message.content for domain in SUPPORTED_DOMAINS) or re.search(clip_url_pattern, message.content):
            # Add reactions for voting
            await message.add_reaction(EMOJI_UPVOTE)
            await message.add_reaction(EMOJI_DOWNVOTE)

    # This is required to process commands if also listening to on_message event
    await bot.process_commands(message)

# Start the bot
bot.run(TOKEN)
