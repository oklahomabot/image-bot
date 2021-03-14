import os
import discord
import sqlite3
from discord.ext import commands
from datetime import datetime, timezone
from .images import pixabay_url_search


class CCguild():
    def __init__(self, id, name='Not Set', home=0, owner='Not Saved', listen=0):
        self.guildID = id
        self.name = name
        self.homechannelID = home
        self.ownerID = owner
        self.listen = listen

    def __str__(self):
        return f'CCguild object, guildID={self.id}'


class CCuser():
    def __init__(self, guildID, userID, name='No Name', exp=0, explevel=0, msgCount=0):
        self.guildID = guildID
        self.userID = userID
        self.name = name
        self.exp = exp
        self.explevel = explevel
        self.msgCount = msgCount

    def __str__(self):
        return f'CCuser object, UserID={self.id}'


class dbstuff(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener("on_message")
    async def msgcount(self, message):
        if message.author == self.client or message.author.bot:
            return

        if not user_exists(message.guild.id, message.author.id):
            # make new user
            tmpuser = CCuser(message.guild.id,
                             message.author.id, name=message.author.name)
            add_new_user(tmpuser)

        # perform per message activities (exp/level/msgcount)
        tmpuser = get_user(message.guild.id, message.author.id)
        tmpuser.msgCount += 1
        # check for exp level promotion (user 5 points from promotion?)
        if exp_level(tmpuser.explevel+1) - tmpuser.exp <= 5:
            tmpuser.explevel += 1
            await message.channel.send(
                f'Congratulations {message.author.name}! You have promoted to exp level {tmpuser.explevel}')
        tmpuser.exp += 5
        save_user(tmpuser)
        # print(f'User {message.author.name} in guild {message.guild} sent a message')

    @commands.command(aliases=['BI', 'bi', 'Bi', 'BOTINFO', 'BotInfo'])
    async def botinfo(self, ctx):

        embed = discord.Embed(
            title='🤖Bot Information🤖', colour=discord.Colour.blue(), timestamp=datetime.now(tz=timezone.utc))

        embed.set_thumbnail(url=self.client.user.avatar_url)

        mh = 0
        for i in self.client.guilds:

            mh += len([m for m in i.members if not m.bot])

        try:
            owner_id = f'<@!{self.client.owner_id}>'
        except:
            owner_id = 'Not defined in commands.Bot.owner_id'

        fields = [("Name - prefix", f'{self.client.user.name} - \"{self.client.command_prefix}\"', True),
                  (":trophy: Owner", owner_id, True),
                  ("SKYNET SECRET 🆔", self.client.user.id, False),
                  (":sunglasses: Server Count", int(
                      len(list(self.client.guilds))), True),
                  ('🦮Trolling ', f'{mh} members',
                   True), ("Favorite Cookbook", "Serving Humans", True),
                  ("📝Invite me", "[Click Here to Add Me](https://discord.com/api/oauth2/authorize?client_id=804002208302891079&permissions=2148002880&scope=bot)", True)]

        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

        embed.set_footer(
            text=f'Requested by: {ctx.author.name}', icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)

    @commands.command(aliases=['erase'], hidden=True)
    async def purge(self, ctx, num=2):
        'Admin delete'
        if ctx.author.id == self.client.owner_id:
            await ctx.channel.purge(limit=num+1)
        else:
            if ctx.author.id == 793433316258480128:
                await ctx.send('Not for you **sniper** :smile:')
            else:
                await ctx.send("I don\'t feel compliant right now")

    @commands.command(aliases=['guilds', 'my_guilds', 'listguilds', 'servers', 'my_servers'], hidden=False)
    async def list_guilds(self, ctx):
        ''' Returns a list of servers where Cupcake is a member '''

        temp_txt, index = '', 0
        async for guild in self.client.fetch_guilds(limit=150):
            index += 1
            temp_txt = temp_txt + \
                f'**{index})** {guild.name}\n'
        embed = discord.Embed(title=f"{self.client.user.display_name}\'s Servers", colour=discord.Colour(
            0xE5E242), description=temp_txt)

        pic_url = await pixabay_url_search(ctx, 'servers')
        embed.set_image(url=pic_url)

        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)

        await ctx.send(embed=embed)

    @commands.command(aliases=['finduser', 'user', 'userinfo'], hidden=False)
    async def user_info(self, ctx, *, person=None):
        '''
        Returns stats about a user on current server.
        If no user given returns message author's stats
        User (person) mention may be ID, name or @mention
        '''
        if (not person) or (person in ['me', 'ME']):
            tmp_member = ctx.message.author
        else:
            # retrieve member object using person (id or user.name or member reference)
            try:
                tmp_member = await commands.converter.MemberConverter().convert(ctx, person)
            except:
                await ctx.send(f"I don\'t know {person}, lets just say **YOU** are the best.")
                tmp_member = ctx.message.author

        if user_exists(ctx.guild.id, tmp_member.id):
            info = get_user(ctx.guild.id, tmp_member.id)
            embed = discord.Embed(
                title=f'{info.name}', colour=discord.Colour.blue())
            temp = ''
            temp = ((f'- ID: {info.userID}\n') +
                    (f'- MsgCount: {info.msgCount}\n') +
                    (f'- Exp Points: {info.exp}\n') +
                    (f'- Exp Level: {info.explevel}\n') +
                    ('- Is User a bot?: '))
            temp = temp + ('YES' if tmp_member.bot else 'NO')
            embed.add_field(name=f'{ctx.guild} STATS', value=temp)
            embed.set_image(url=tmp_member.avatar_url)
            embed.set_thumbnail(
                url='https://images.pexels.com/photos/3769697/pexels-photo-3769697.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=750&w=1260')

            await ctx.send(embed=embed)
        else:
            await ctx.send(f'Looked for {tmp_member.name} on server {ctx.guild.name} : result - RECORD NOT FOUND in db')

    @commands.command(aliases=['top', 'TOP', 'leaders'], hidden=False)
    async def top_points(self, ctx, how_many: int = 3):
        ''' 
        Reports in chat top exp earners on this server
        A value of 1-10 may be used for how many users
        you want on the list
        '''
        if (1 <= how_many <= 10):
            tmp_str = ''
            tmp_list = top_exp(ctx.guild.id, how_many)

            embed = discord.Embed(
                title=f'TOP {len(tmp_list)} Users', description='(EXPERIENCE POINTS)', colour=discord.Colour.blue())
            for user_data in tmp_list:
                embed.add_field(
                    name=f'{user_data[0][:17]}', value=f'EXP : **{user_data[1]}** LEVEL : {user_data[2]}')
            embed.set_image(
                url='https://images.pexels.com/photos/5731842/pexels-photo-5731842.jpeg?auto=compress&cs=tinysrgb&dpr=3&h=750&w=1260')

            if ctx.message.author.avatar is not None:
                embed.set_thumbnail(
                    url=ctx.message.author.avatar_url_as(size=64))
            await ctx.send(embed=embed)
        else:
            await ctx.send(f'{how_many} invalid - Please use a whole number 1-10 or leave blank for top 3')

    @commands.command(aliases=['num1', 'best'], hidden=False)
    async def number_one(self, ctx, *, person=None):
        '''
        Cupcake decides who is the best
        User (person) mention may be ID, name or @mention
        '''

        if not person and ctx.guild.id == 790518150306332673:  # Sweetie is best on my server
            tmp_member = await commands.converter.MemberConverter().convert(ctx, 'SweetieCakesMel#9791')
        else:
            if (not person) or (person in ['me', 'ME']):
                tmp_member = ctx.message.author
            else:
                # retrieve member object using person (id or user.name or member reference)
                try:
                    tmp_member = await commands.converter.MemberConverter().convert(ctx, person)
                except:
                    await ctx.send(f"I don\'t know {person}, lets just say **YOU** are the best.")
                    tmp_member = ctx.message.author

        # Insert embed creation from member info here
        embed = discord.Embed(
            title=f':star_struck: {tmp_member.name} :star_struck: ', description='**SIMPLY THE BEST AROUND**',
            colour=discord.Colour.blue())
        embed.set_image(url=tmp_member.avatar_url)
        embed.set_thumbnail(url=self.client.user.avatar_url_as(size=64))
        await ctx.send(embed=embed)

# Helper Functions


def exp_level(level=0):
    '''
    Returns base exp value for exp level
    '''
    level_dic = {0: 0, 1: 100, 2: 220, 3: 350, 4: 500, 5: 675, 6: 875,
                 7: 1125, 8: 1450, 9: 1850, 10: 2600, 11: 3600, 12: 4800, 13: 6300, 14: 8000, 15: 10000, 16: 1000000}
    return level_dic[level]


''' SQLite3 Database Stuff '''
# Creates connection to db in current directory
conn = sqlite3.connect(os.path.join(
    "./", "cogs", "images", "data", 'images.db'))
c = conn.cursor()


def add_guild_if_new(g: CCguild):
    with conn:
        text = f"INSERT OR IGNORE INTO guilds VALUES (?, ?, ?, ?, ?)"
        c.execute(text, (g.guildID, g.name, g.homechannelID, g.ownerID, g.listen))


def top_exp(guildID=None, how_many: int = 3):
    ''' queries db and returns list username/point/level tuples '''
    if not guildID:
        return
    if not(10 >= how_many >= 1):
        how_many = 3
    with conn:
        c.execute(
            f"SELECT name, exp, explevel from users WHERE guildID={guildID}")
        result = c.fetchall()
        # sort by second element of tuple (exp)
        result.sort(key=lambda x: x[1], reverse=True)
        # print(result)
        if len(result) <= how_many:
            return result
        else:
            return result[:how_many]


def user_exists(guildID=-1, userID=-1):
    ''' returns boolean if guild/user record found in db table users '''
    with conn:
        c.execute(
            f"SELECT COUNT(*) from users WHERE guildID={guildID} AND userID={userID}")
        if c.fetchone()[0] >= 1:
            return True
        else:
            return False


def get_user(guildID=None, userID=None):
    # creates/returns CCuser object from db data
    with conn:
        c.execute(
            f"SELECT * from users WHERE guildID={guildID} AND userID={userID}")
        result = c.fetchone()
        CCuserOBJECT = CCuser(result[0], result[1],
                              result[2], result[3], result[4], result[5])
        return CCuserOBJECT


def add_new_user(user: CCuser):
    with conn:
        text = f"INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?)"
        c.execute(text, (user.guildID, user.userID, str(user.name), user.exp,
                         user.explevel, user.msgCount))


def save_user(user: CCuser):
    # takes CCuser object and updates db
    with conn:
        text = f'UPDATE users SET guildID = {user.guildID}, userID = {user.userID}, name = \"{user.name}\",'
        text = text + \
            f'exp = {user.exp}, explevel = {user.explevel}, msgcount = {user.msgCount} '
        text = text + \
            f'WHERE guildID = {user.guildID} AND userID = {user.userID}'
        c.execute(text)


def setup(client):  # Cog setup command
    client.add_cog(dbstuff(client))
