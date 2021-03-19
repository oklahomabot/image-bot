import os
import sys
import traceback
import shutil
import sqlite3
import discord
import re
from discord import user
from discord import client
from discord.ext.commands.core import is_owner
import requests
import urllib.parse
from discord.ext import commands
from PIL import Image, ImageDraw
from io import BytesIO
from random import randint
from dotenv import load_dotenv
from datetime import datetime, timezone

''' SQLite3 Database Stuff '''
# Creates connection to db in current directory
conn = sqlite3.connect(os.path.join(
    "./", "cogs", "images", "data", 'images.db'))
c = conn.cursor()

bot_folder = os.path.join('./', 'cogs', 'images')
master_folder = os.path.join(bot_folder, 'masters')
output_folder = os.path.join(bot_folder, 'output')
gif_folder = os.path.join(bot_folder, 'gifs')
db_folder = os.path.join(bot_folder, 'data')
junk_folder = os.path.join(bot_folder, 'junk')


class images(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.owner = discord.ClientUser

    def editor_only():
        def predicate(ctx):
            ok = ctx.author.id in get_editor_IDs()
            return ok
        return commands.check(predicate)

    @commands.Cog.listener("on_ready")
    async def approve_bot_owner(self):
        my_info = await self.client.application_info()
        self.owner = my_info.owner
        new_editor(my_info.owner)
        new_editor(self.client.user)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            text = (f'Sorry, I do not understand the command **{ctx.invoked_with}**.\n')+(
                f'Remember you can always use \"{self.client.command_prefix}help\"')
            await ctx.send(text)
            return
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f'{ctx.author} You are not authorized to run command \"{ctx.command.qualified_name}\"')
            return
        if isinstance(error, commands.errors.BadArgument):
            text = (f'That was confusing {ctx.author.display_name} ... \n')+(
                f'Remember you can always use \"{self.client.command_prefix}help {ctx.command.qualified_name}\"')
            await ctx.send(text)
            return
        print('Ignoring exception in command {}:'.format(
            ctx.command), file=sys.stderr)
        traceback.print_exception(
            type(error), error, error.__traceback__, file=sys.stderr)

    @commands.command(aliases=['list_editors', 'show_editors'], hidden=False)
    async def editor_list(self, ctx):
        '''Shows list of users authorized to edit fun_images'''
        embed = discord.Embed(title='EDITORS', colour=discord.Colour.blue())
        embed.set_thumbnail(url=ctx.message.author.avatar_url_as(size=64))
        embed.set_image(
            url='https://images.pexels.com/photos/159984/pexels-photo-159984.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=750&w=1260')
        e_dic = editors_dic()
        temp = "\n".join([(f'**{e_dic[k]}** id: {k}') for k in e_dic.keys()])
        embed.add_field(
            name=(':arrow_down: Fun_Image Bosses :arrow_down:'), value=temp)
        await ctx.send(embed=embed)

    @commands.command(aliases=['addeditor', 'approve_editor'], hidden=True)
    @editor_only()
    async def add_editor(self, ctx, *, user):
        '''(editor only) Approve a user to edit fun_images '''
        if not user:
            await ctx.send(f'A user must be referenced to use this command')
            return

        try:
            user = await commands.converter.MemberConverter().convert(ctx, user)
        except:
            await ctx.send(f"I couldn\'t find {user} on this server ... nothing has changed")
            return

        new_editor(user)
        await ctx.send(f'User {user.display_name} added to approved editor list')

    @commands.command(aliases=['del_editor', 'deleditor'], hidden=True)
    @editor_only()
    async def delete_editor(self, ctx, *, user=None):
        '''(editor only) Remove a user from approved fun_image editor list '''

        if not user:
            await ctx.send(f'A user must be referenced to use this command')
            return
        try:
            user = await commands.converter.MemberConverter().convert(ctx, user)
        except:
            await ctx.send(f"I couldn\'t find {user} on this server ... nothing has changed")
            return

        if user == self.owner or user == self.client.user:
            await ctx.send(
                (f'{self.owner.display_name} and I must remain on the editor list.\n') +
                (f'I cannot do what you ask {ctx.author.display_name}.'))
            return

        remove_editor(user)
        await ctx.send(f'User {user.display_name} removed from the approved editor list')

    @commands.command(aliases=['pic', 'picture'], hidden=False)
    async def get_pic(self, ctx, *, search_txt=None):
        '''
        Provides an image using your search words (optional)
        Pictures retrieved using Pixabay's API
        '''
        if search_txt:
            embed = discord.Embed(title=f":mag: **{search_txt}** :mag:", colour=discord.Colour(
                0xE5E242), description=f"image provided by [Pixabay.com\'s API](https://pixabay.com/)")
        else:
            embed = discord.Embed(title=f"RANDOM PICTURE ... Good Luck :smile:", colour=discord.Colour(
                0xE5E242), description=f"image provided by [Pixabay.com\'s API](https://pixabay.com/)")

        result_link = await pixabay_url_search(ctx, search_txt)

        embed.set_image(url=result_link)
        embed.set_thumbnail(
            url=self.client.user.avatar_url_as(size=64))
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)

        await ctx.send(embed=embed)

    @commands.command(aliases=['ani'], hidden=False)
    async def animu(self, ctx, *, category=None):
        '''View an animu in category wink, hug, pat or face-palm'''
        if category == 'face palm':
            category = 'face-palm'
        valid_cats = ['wink', 'hug', 'pat', 'face-palm']
        if category not in valid_cats:
            text = f'Please try again selecting a category ex) \"{self.client.command_prefix}animu hug\"\n'
            text = text + 'Valid categories are **'
            text = text + \
                "** , **".join(valid_cats[:-1]) + f' and {valid_cats[-1]}**'
            await ctx.send(text)
            return

        url = f'https://some-random-api.ml/animu/{category}'
        response = requests.get(url)

        if response.status_code != 200:
            await ctx.send(f"Something happened, I couldn\'t get your image {ctx.author.display_name} :(")
            return

        embed = discord.Embed(
            title=f"**{category}** Animu Image", colour=discord.Colour(0xE5E242),
            description=f"image provided by [some-random-API.ml](https://some-random-API.ml/)",
            timestamp=datetime.now(tz=timezone.utc))
        embed.set_image(url=response.json()['link'])
        embed.set_thumbnail(url=self.client.user.avatar_url_as(size=64))
        embed.set_footer(
            text=f'Requested by: {ctx.author.name}', icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)

    @commands.command(aliases=['trigger', 'triggered', 'gay', 'glass', 'wasted'], hidden=False)
    async def trigger_someone(self, ctx, *, user=None):
        '''
        Use trigger, gay, glass or wasted and mention a friend
        This command uses some-random-API interface to produce images
        '''
        await ctx.send(f'Do not forget about karma {ctx.author.name} ...')

        # Convert user to user or member / use author
        if user:
            try:
                user = await commands.converter.MemberConverter().convert(ctx, user)
            except:
                await ctx.send(f"I don\'t know {user}, lets just use your avatar ...")
                user = ctx.author
        else:
            user = ctx.author

        if ctx.invoked_with in ['trigger', 'trigger_someone']:
            image_name = 'triggered'
        else:
            image_name = ctx.invoked_with

        getVars = {'avatar': user.avatar_url_as(format='png')}
        url = f'https://some-random-api.ml/canvas/{image_name}/?'
        response = requests.get(
            url + urllib.parse.urlencode(getVars), stream=True)

        if response.status_code != 200:
            await ctx.send('Well ... that did not work for some reason.')
            return

        # Set decode_content value to True, otherwise the downloaded image file's size will be zero.
        response.raw.decode_content = True

        out_path = os.path.join(gif_folder, 'randomAPI', (f'{image_name}.gif'))
        with open(out_path, 'wb+') as out_file:
            shutil.copyfileobj(response.raw, out_file)
        del response

        await ctx.send(file=discord.File(out_path))

    @commands.command(aliases=[x.split('.')[0] for x in os.listdir(master_folder)], hidden=False)
    async def fun_images(self, ctx, *, user=None):
        '''
        Makes a fun_image using either your profile pic and/or another user's
        Usage example 'dog' or 'dog oklahoma_bot'
        List of finished images may be found via 'fun_list'
        '''
        cmd = ctx.invoked_with

        if cmd in get_command_list(approved=False):
            await ctx.send(f'{cmd} is not developed yet, you get what you get :smile:\nTry fun_list for a list of developed fun images.')

        # Check user validity using converter / if bad use message.author for user
        if (not user) or (user in ['me', 'ME']):
            user = None
        else:
            # retrieve member object using person (id or user.name or member reference)
            try:
                user = await commands.converter.MemberConverter().convert(ctx, user)
            except:
                await ctx.send(f"I don\'t know {user}, lets just use your avatar ...")
                user = None

        out_file = await make_funfile(cmd, ctx.author, user)

        await ctx.send(file=discord.File(out_file))

    @commands.command(aliases=['slapmore', 'slap_more', 'slapagain', 'slap_again', 're-slap'], hidden=False)
    async def reslap(self, ctx, delay: int = 500):
        '''
        Last person slapped gets slapped over and over
        Optional delay can be used 100 - 1000 (lower number is faster)
        ex) "reslap 500"
        '''

        if not (100 <= delay <= 1000):
            delay = 500
        path = os.path.join(output_folder, 'slapoutput.png')
        im1 = Image.open(path)
        im1 = im1.copy()
        im2 = im1.copy()
        im2 = im2.transpose(Image.FLIP_LEFT_RIGHT)
        img_list = [im1, im2]
        outfile = os.path.join(gif_folder, "slapmore.gif")
        img_list[0].save(outfile,
                         save_all=True, append_images=img_list[1:], optimize=True, duration=delay, loop=0)
        file = (discord.File(outfile))
        await ctx.send(file=file)

    @commands.command(aliases=['alter', 'edit', 'change'], hidden=True)
    @editor_only()
    async def edit_command(self, ctx, command_name=None, column=None, new_value=None):
        '''(editor only) Change parameters for creating fun_image (editor only)'''
        columns = {}
        columns['imgcount'] = "The number of user profile pics this command uses ex) edit dog **imgcount 2**"
        columns['size1'] = "image1\'s size in pixels (same x and y is normal) ex) edit dog **size1 200,200**"
        columns['rot1'] = "ccw rotation in degrees ex) edit dog **rot1 180**"
        columns['paste1'] = "(x,y) where image 1 will be pasted onto background image ex) edit dog **paste1 120,200**"
        columns['size2'] = "image2\'s size in pixels (same x and y is normal) ex) edit dog **size2 200,200**"
        columns['rot2'] = "ccw rotation in degrees for image 2 ex) edit dog **rot1 180**"
        columns['paste2'] = "(x,y) where image 2 will be pasted onto background image ex) edit dog **paste2 120,200**"
        columns['approved'] = "image is approved for use ex) edit dog **approved true**"

        # Check for valid command/column/value - give help and exit if not given
        if command_name not in image_dic.keys():
            temp_str = (f'missing valid command name ... **{command_name}** is not valid') + (
                f'\nCommand names : {"**"+"** **".join(image_dic.keys())}'+'**')
            await ctx.send(temp_str)
            return

        if column not in columns.keys():
            temp_str = f'Requires valid column_name ex) edit dog **size1** 200,200 ...\n column names are : {" ".join(columns.keys())}'
            await ctx.send(temp_str)
            return

        if not new_value:
            await ctx.send(f'Value required : {columns[column]}')
            return

        if column in ['imgcount', 'rot1', 'rot2']:
            new_value = int(new_value)
        elif column in ['size1', 'size2', 'paste1', 'paste2']:
            new_value = tuple(map(int, re.findall(r'[0-9]+', new_value)))
        elif column in ['approved']:
            if new_value.lower() in ['true', 'yes', '1']:
                new_value = True
            else:
                new_value = False

        image_dic[command_name][column] = new_value

        await make_funfile(command_name, ctx.message.author, self.client.user)
        await ctx.send(f'MASTER **{command_name} {column}** edited.')
        await self.show_command_values(ctx=ctx, command_name=command_name)

    @commands.command(aliases=['funlist', 'pic_list', 'piclist'], hidden=False)
    async def fun_list(self, ctx):
        '''
        Displays a list of "fun image" commands like 'dog' or 'slap' ...
        '''
        my_list = get_command_list()
        temp_str = (', ').join(my_list)
        temp_str = temp_str + '\nex) dog oklahoma_bot'
        embed = discord.Embed(title='FUN IMAGE COMMANDS',
                              description='You can use these by themselves or mention another user', colour=discord.Colour.blue())
        embed.set_thumbnail(url=ctx.message.author.avatar_url_as(size=64))
        embed.set_image(
            url='https://cdn.tinybuddha.com/wp-content/uploads/2015/10/Having-Fun.png')
        embed.add_field(name='**Command List**', value=temp_str)
        await ctx.send(embed=embed)

    @commands.command(aliases=['start_over', 'cancel_edit', 'canceledit', 'cancel_edits', 'canceledits'], hidden=True)
    @editor_only()
    async def reload_dic(self, ctx):
        '''(editor only)'''
        global image_dic
        image_dic = make_dic_from_db()
        await ctx.send('All pic information reloaded from db ... temporary changes are gone. ')

    @commands.command(aliases=['show'], hidden=True)
    @editor_only()
    async def show_command_values(self, ctx, command_name='NOT ENTERED'):
        '''(editor only) Lists parameters for one fun_image'''

        # Exit if not in dictionary
        if not command_name in image_dic.keys():
            await ctx.send(f'**{command_name}** not in dictionary **image_dic** yet')
            return

        embed = discord.Embed(
            title=f':arrow_up: Last \"{command_name}\" Image Created :arrow_up:', description=':arrow_down: **current** image manipulation info\n(may not be last info used)', colour=discord.Colour.red())

        embed.set_thumbnail(url=ctx.message.author.avatar_url_as(size=64))

        temp = f'paste1: {image_dic[command_name]["paste1"]} rot1: {image_dic[command_name]["rot1"]} size1: {image_dic[command_name]["size1"]}'
        embed.add_field(name=f'avatar 1', value=temp, inline=False)

        if image_dic[command_name]["imgcount"] == 2:
            temp = f'paste2: {image_dic[command_name]["paste2"]} rot2: {image_dic[command_name]["rot2"]} size2: {image_dic[command_name]["size2"]}'
            embed.add_field(name=f'avatar 2', value=temp, inline=False)

        embed.add_field(
            name=f'summary', value=f'imgcount : {image_dic[command_name]["imgcount"]} approved : {"YES" if image_dic[command_name]["approved"] else "NO"}', inline=False)

        file = discord.File(os.path.join(
            output_folder, command_name + 'output.png'))
        await ctx.send(file=file, embed=embed)

    @commands.command(aliases=['save_img', 'saveimage', 'savecommand', 'savepic', 'save_pic'], hidden=True)
    @editor_only()
    async def save_command(self, ctx, command_name='UNDEFINED-COMMAND'):
        '''(editor only) Saves temporary image edits to db'''
        if command_name in image_dic.keys():
            save_command_to_db(command_name)
            await ctx.send(f'{command_name} saved')
        else:
            await ctx.send(f'{command_name} NOT FOUND in image_dic, nothing has been saved')

    @commands.command(aliases=['del_img', 'delete_img' 'delimage', 'del_image'], hidden=True)
    @editor_only()
    async def delete_command(self, ctx, command_name='UNDEFINED-COMMAND'):
        '''(editor only) DELETES one fun image command from the database and image_dic'''

        if command_name in image_dic.keys():
            delete_command_from_db(command_name)
        else:
            await ctx.send(f'{command_name} NOT FOUND in image_dic, nothing has been deleted')
            return

        move_file(master_folder, junk_folder,
                  image_dic[command_name]['filename'])

        del image_dic[command_name]

    @commands.command(aliases=['unapproved', 'notdone'], hidden=True)
    @editor_only()
    async def unfinished(self, ctx):
        '''(editor only)Lists fun_images not approved yet'''
        await ctx.send(f'Commands not yet finished : {get_command_list(approved=False)}')

    @commands.command(aliases=['dryer', 'spindry'], hidden=False)
    async def dry(self, ctx, *, user=None):
        ''' Dry your friends off ... no idea why they are wet though '''
        if not user:
            user = ctx.message.author
        else:
            try:
                user = await commands.converter.MemberConverter().convert(ctx, user)
            except:
                await ctx.send(f"I don\'t know {user}, lets just use your avatar ...")
                user = ctx.message.author

        asset = user.avatar_url_as(format=None, static_format='png', size=128)
        data = BytesIO(await asset.read())
        im = Image.open(data)
        im = im.resize((295, 295))
        im = convert_mode(im)
        im = mask_circle(im)

        # Make first image (dryer green-stopped)
        f = Image.open(os.path.join(gif_folder, 'dryer', 'dryer.png'))
        back1 = f.copy()
        back1.alpha_composite(im, dest=(102, 147))
        f = Image.open(os.path.join(gif_folder, 'dryer', 'reddryer.png'))
        back2 = f.copy()

        gif_images = []
        gif_images.append(back1)

        # Add red dryer images to image list
        # rotating cw(30)*12 then ccw(330)*12
        for rot_amount in [30, 330]:
            for _ in range(12):
                im = im.rotate(rot_amount)
                back2.alpha_composite(im, dest=(102, 147))
                gif_images.append(back2.copy())

        # Add green dryer images to list
        for _ in range(5):
            gif_images.append(back1)

        # Assemble and publish animated gif
        outfile = os.path.join(gif_folder, 'dryer', "dryer.gif")
        gif_images[0].save(outfile, save_all=True, append_images=gif_images[1:],
                           optimize=True, duration=100, loop=0, interlace=False, disposal=2)
        file = (discord.File(outfile))
        await ctx.send(file=file)


# HELPER FUNCTIONS

def master_folder_command_list():
    filenames = os.listdir(master_folder)
    return_list = []
    for file in filenames:
        return_list.append(file.split('.')[0])

    return return_list


async def make_funfile(cmd, user1, user2=None):
    '''
    Creates image using 1 or two Discord user/member(s) avatars
    Background image is taken from <<master_folder>> specified by <cmd>.
    Pasting parameters stored in <<image_dic>>.
    Typical use - user1 is invoking message's author
    This function returns the file_path for the new image.
    '''

    info = image_dic[cmd]
    im = Image.open(os.path.join(master_folder, info['filename']))
    im = im.copy()

    # First image pasted will be user1 unless user2 specified
    if user2:
        asset = user2.avatar_url_as(format=None, static_format='png', size=128)
    else:
        asset = user1.avatar_url_as(format=None, static_format='png', size=128)

    data = BytesIO(await asset.read())
    im1 = Image.open(data)
    im1 = im1.resize(info['size1'])
    im1 = convert_mode(im1)
    im1 = mask_circle(im1)
    if info['rot1']:
        im1 = im1.rotate(info['rot1'])
    im.alpha_composite(im1, dest=info['paste1'])

    # Second image pasted will be user1 if command requires second image pasting
    if (info['imgcount'] == 2) and (user2):
        asset = user1.avatar_url_as(format=None, static_format='png', size=128)
        data = BytesIO(await asset.read())
        im2 = Image.open(data)
        im2 = convert_mode(im2)
        im2 = im2.resize(info['size2'])
        im2 = mask_circle(im2)
        if info['rot2']:
            im2 = im2.rotate(info['rot2'])
        im.alpha_composite(im2, dest=info['paste2'])

    # save results and send return new_img_path
    new_img_path = os.path.join(output_folder, f'{cmd}output.png')
    im.save(new_img_path)
    # file = discord.File(out_file)
    return new_img_path


async def pixabay_url_search(ctx, search_by=None):
    '''
    Uses Pixabay's API to search for a pic url based on search_by
    If None given a random one will be supplied
    '''
    if search_by:
        getVars = {'key': PIXABAY_API_KEY,
                   'q': search_by, 'safesearch': 'true', 'page': 1}
    else:
        getVars = {'key': PIXABAY_API_KEY, 'safesearch': 'true', 'page': 1}

    url = 'https://pixabay.com/api/?'
    response = requests.get(url + urllib.parse.urlencode(getVars))

    if response.status_code == 200:
        data = response.json()
        if len(data['hits']) > 0:
            rndpic = randint(0, len(data['hits'])-1)
            return data['hits'][rndpic]['webformatURL']
        else:
            return ('https://cdn.dribbble.com/users/283708/screenshots/7084432/media/451d27c21601d96114f0eea20d9707e2.png?compress=1&resize=400x300')


def process_new_images():

    # Create new db record if necessary
    with conn:
        for filename in os.listdir(master_folder):
            # check if record already exists
            c.execute(
                f"SELECT EXISTS(SELECT 1 FROM paste_info WHERE command='{filename.split('.')[0]}')")
            if not bool(c.fetchone()[0]):  # New Command/Image not in db

                print(
                    f'**NEW MASTER PIC DETECTED** {master_folder} + {filename}')
                filename = convert_master_image_to_png(filename)
                resize_max_dimension(master_folder, filename, 1500)

                # make new db record using default values
                text = "INSERT OR IGNORE INTO paste_info VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?,?)"
                c.execute(text, (filename.split('.')[0], 1, 300, 300, 0,
                                 0, 0, 300, 300, 0, 0, 0, filename, 0))

        return


def make_dic_from_db():

    process_new_images()

    with conn:
        # Index is command_name and values are stored in a dictionary
        c.execute("SELECT * FROM paste_info")
        rows = c.fetchall()
        return_dic = {}
        usable_commands = master_folder_command_list()
        for row in rows:
            # skip commands in db w/o images in masters
            if row[0] in usable_commands:
                info = {}
                info['name'] = row[0]
                info['imgcount'] = row[1]
                info['size1'] = tuple([row[2], row[3]])
                info['rot1'] = row[4]
                info['paste1'] = tuple([row[5], row[6]])
                info['size2'] = tuple([row[7], row[8]])
                info['rot2'] = row[9]
                info['paste2'] = tuple([row[10], row[11]])
                info['filename'] = row[12]
                info['approved'] = row[13]
                return_dic[row[0]] = info

        generate_missing_output_images()
        return return_dic


def generate_missing_output_images():
    '''
    Compare images in master folder and make corresponding
    images in output folder if missing
    '''
    master_filenames = os.listdir(master_folder)
    cmd_list = [f.split('.')[0] for f in master_filenames]
    outpics = os.listdir(output_folder)
    outpics = [f.replace("output", "").split('.')[0] for f in outpics]
    missing = set(cmd_list) - set(outpics)

    if missing:
        file_dic = {cmd_list[i]: master_filenames[i]
                    for i in range(len(cmd_list))}
        print(
            f'COG image : Adding MISSING output files : {missing}')
        for file in missing:
            fn = file_dic[file]
            new_fn = fn.split('.')[0] + 'output.' + fn.split('.')[1]
            shutil.copyfile(os.path.join(
                master_folder, file_dic[file]), os.path.join(output_folder, new_fn))

    return


def save_command_to_db(cmd=None):
    with conn:
        temp = ('UPDATE paste_info SET '
                'imgcount = ?, sizex1 = ?, sizey1 = ?,rot1 = ?, '
                'pastex1 = ?, pastey1 = ?, sizex2 = ?, sizey2 = ?, '
                'rot2 = ?, pastex2 = ?, pastey2 = ?, approved = ? '
                'WHERE command = ' + f'\"{cmd}\"')
        info = image_dic[cmd]
        values = (info['imgcount'], info['size1'][0], info['size1'][1], info['rot1'],
                  info['paste1'][0], info['paste1'][1], info['size2'][0],
                  info['size2'][1], info['rot2'], info['paste2'][0], info['paste2'][1],
                  info['approved'])
        c.execute(temp, values)


def delete_command_from_db(cmd=None):
    with conn:
        temp = ('DELETE FROM paste_info WHERE command = ' + f'\"{cmd}\"')
        c.execute(temp)
        print(f'COG images : fun image command {cmd} deleted from db')


def get_command_list(approved=True):
    approved_list = []
    unfinished = []
    for command_name in image_dic.keys():
        if image_dic[command_name]['approved']:
            approved_list.append(command_name)
        else:
            unfinished.append(command_name)
    approved_list.sort()
    unfinished.sort()
    return approved_list if approved else unfinished


def resize_max_dimension(folder, filename, max_dimension):
    '''
    referenced image will be resized such that largest
    dimension will equal max_dimension
    '''
    im = Image.open(os.path.join(folder, filename))
    im = im.copy()
    x, y = im.size
    xbiggest = True if x >= y else False
    ratio = max_dimension/x if xbiggest else max_dimension/y
    newsize = int(x*ratio), int(y*ratio)
    im = im.resize(newsize)

    im.save(os.path.join(folder, filename))

    return


def mask_circle(im):
    bigsize = (im.size[0] * 3, im.size[1] * 3)
    mask = Image.new('L', bigsize, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + bigsize, fill=255)
    mask = mask.resize(im.size, Image.ANTIALIAS)
    im.putalpha(mask)

    return im


def move_file(from_folder, to_folder, filename, newname=None):
    if not newname:
        newname = filename
    dest = shutil.move(os.path.join(from_folder, filename),
                       os.path.join(to_folder, newname))
    return


def convert_master_image_to_png(filename):

    im = Image.open(os.path.join(master_folder, filename))
    im = im.copy()
    if im.mode == 'RGBA':
        return filename

    try:
        im = im.convert('RGBA')
        im.putalpha(255)
        if im.mode == 'RGBA':
            new_filename = filename.split('.')[0]+'.png'
            move_file(master_folder, junk_folder, filename)
            im.save(os.path.join(master_folder, new_filename))
        filename = new_filename
        print(
            f'Images COG : convert_master_image_to_png successfully converted/saved as {filename}')
    except:
        print(
            f'Images COG : convert_master_image_to_png **FAILED** to convert/saved {filename}')

    return filename


def convert_mode(im):
    if im.mode != 'RGBA':
        im = im.convert('RGBA')
        im.putalpha(255)
    return im


def new_editor(user):
    with conn:
        text = f'INSERT OR IGNORE INTO editors (userID, name) VALUES ({user.id}, \"{user.display_name}\")'
        c.execute(text)
    return


def remove_editor(user):
    with conn:
        text = f'DELETE FROM editors WHERE userID = {user.id}'
        c.execute(text)
    return


def editors_dic():
    return_dic = {}

    with conn:
        c.execute('SELECT * FROM editors')
        rows = c.fetchall()

        for row in rows:
            return_dic[row[0]] = row[1]

    return return_dic


def get_editor_IDs():
    with conn:
        c.execute('SELECT userID FROM editors')
        rows = c.fetchall()
    return [id[0] for id in rows]


image_dic = make_dic_from_db()

# get api token for image APIs
load_dotenv()
PIXABAY_API_KEY = os.getenv('PIXABAY_API_KEY')


def setup(client):  # Cog setup command
    client.add_cog(images(client))


# admin_commands + hide commands from help menu
