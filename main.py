import datetime
import logging
import os
import traceback
import typing

import base64
import zstd
import png

import discord
from discord.ext import commands
from dotenv import load_dotenv

class CustomBot(commands.Bot):
    _uptime: datetime.datetime = datetime.datetime.utcnow()

    def __init__(self, prefix: str, *args: typing.Any, **kwargs: typing.Any) -> None:
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(*args, **kwargs, command_prefix=commands.when_mentioned_or(prefix), intents=intents)
        self.logger = logging.getLogger(self.__class__.__name__)

    async def on_error(self, event_method: str, *args: typing.Any, **kwargs: typing.Any) -> None:
        self.logger.error(f"An error occurred in {event_method}.\n{traceback.format_exc()}")

    async def on_ready(self) -> None:
        self.logger.info(f"Logged in as {self.user} ({self.user.id})")

    def run(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        load_dotenv()
        try:
            super().run(str(os.getenv("TOKEN")), *args, **kwargs)
        except (discord.LoginFailure, KeyboardInterrupt):
            self.logger.info("Exiting...")
            exit()

    @property
    def user(self) -> discord.ClientUser:
        assert super().user, "Bot is not ready yet"
        return typing.cast(discord.ClientUser, super().user)

    @property
    def uptime(self) -> datetime.timedelta:
        return datetime.datetime.utcnow() - self._uptime

class Blueprint:
    version: int
    checksum: bytearray
    width: int
    height: int
    logicImage: bytearray

def parseBlueprint (blueprint):
    blueprint = blueprint.replace("```", "")
    blueprint = blueprint.replace("\'", "")
    if not blueprint.startswith("VCB+") and not blueprint.startswith("bVCB+"):
        raise Exception("invalid vcb blueprint - header error")
    if blueprint.startswith("VCB+"):
        blueprint = blueprint[4:] # strip the VCB+
    if blueprint.startswith("bVCB+"):
        blueprint = blueprint[5:] # strip the bVCB+
    try:
        blueprint = base64.b64decode(blueprint)
    except Exception:
        raise Exception("invalid vcb blueprint - base64 error")
    version = int.from_bytes(blueprint[0:3], "big")
    checksum = blueprint[3:9]
    width = int.from_bytes(blueprint[9:13], "big")
    height = int.from_bytes(blueprint[13:17], "big")
    if version != 0:
        raise Exception("invalid vcb blueprint - unexpected version number: " + str(version))
    if width * height == 0:
        raise Exception("invalid vcb blueprint - blueprint is 0x0")
    curpos = 17
    image = None
    while curpos < len(blueprint):
        blockSize = int.from_bytes(blueprint[curpos:curpos+4], "big")
        layerID = int.from_bytes(blueprint[curpos+4:curpos+8], "big")
        imageSize = int.from_bytes(blueprint[curpos+8:curpos+12], "big")
        if blockSize < 12: # also prevents infinite loops on invalid data if blockSize is 0
            raise Exception("invalid vcb blueprint - invalid layer block size: " + str(blockSize))
        if layerID == 0: # look for logic layer       
            try:
                image = zstd.uncompress(blueprint[curpos+12:curpos+blockSize])
            except Exception:
                raise Exception("invalid vcb blueprint - zstd error")
            # validate uncompressed data length
            if len(image) != imageSize:
                raise Exception("invalid vcb blueprint - unexpected image size: " + str(imageSize))
        # advance to next block
        curpos += blockSize
    # pack into a Blueprint and return
    bp = Blueprint()
    bp.version = version
    bp.checksum = checksum
    bp.width = width
    bp.height = height
    bp.logicImage = image
    return bp

def getstats(blueprint):
    bp = parseBlueprint(blueprint)
    # count pixels in blueprint
    image = bp.logicImage
    counts = {}
    area = 0
    for i in range(0, len(image), 4):
        if image[i+3] > 0:
            rgb = (int(image[i]), int(image[i+1]), int(image[i+2]), int(image[i+3]))
            counts[rgb] = (counts[rgb] if rgb in counts else 0) + 1
            area = area + 1
    # build result message
    totalmessage = []
    totalmessage.append("```\n")
    totalmessage.append("checksum: " + bp.checksum.hex() + "\n")
    totalmessage.append("width:    " + str(bp.width) + "\n")
    totalmessage.append("height:   " + str(bp.height) + "\n")
    totalmessage.append("-----------\n")
    tracecount = 0
    buscount = 0
    def percent (n, total):
        return f" ({int(100.0 * n / total + 0.5)}%)"
    def countMessage (name, counts, rgba):
        nonlocal tracecount
        nonlocal buscount
        nonlocal totalmessage
        if rgba in counts and counts[rgba] > 0 and not (name.startswith("Bus") or name.startswith("Trace")):
            totalmessage.append(name + " pixels: " + str(counts[rgba]) + percent(counts[rgba], bp.width * bp.height) + ", ")
        elif name.startswith("Trace")  and rgba in counts:
            tracecount += counts[rgba]
        elif name.startswith("Bus") and rgba in counts:
            buscount += counts[rgba]
    countMessage("Cross", counts, (102, 120, 142, 255))
    countMessage("Tunnel", counts, (83, 85, 114, 255))
    countMessage("Mesh", counts, (100, 106, 87, 255))
    countMessage("Bus1", counts, (122, 47, 36, 255))
    countMessage("Bus2", counts, (62, 122, 36, 255))
    countMessage("Bus3", counts, (36, 65, 122, 255))
    countMessage("Bus4", counts, (37, 98, 122, 255))
    countMessage("Bus5", counts, (122, 45, 102, 255))
    countMessage("Bus6", counts, (122, 112, 36, 255))
    countMessage("Write", counts, (77, 56, 62, 255))
    countMessage("Read", counts, (46, 71, 93, 255))
    countMessage("Trace1", counts, (42, 53, 65, 255))
    countMessage("Trace2", counts, (159, 168, 174, 255))
    countMessage("Trace3", counts, (161, 85, 94, 255))
    countMessage("Trace4", counts, (161, 108, 86, 255))
    countMessage("Trace5", counts, (161, 133, 86, 255))
    countMessage("Trace6", counts, (161, 152, 86, 255))
    countMessage("Trace7", counts, (153, 161, 86, 255))
    countMessage("Trace8", counts, (136, 161, 86, 255))
    countMessage("Trace9", counts, (108, 161, 86, 255))
    countMessage("Trace10", counts, (86, 161, 141, 255))
    countMessage("Trace11", counts, (86, 147, 161, 255))
    countMessage("Trace12", counts, (86, 123, 161, 255))
    countMessage("Trace13", counts, (86, 98, 161, 255))
    countMessage("Trace14", counts, (102, 86, 161, 255))
    countMessage("Trace15", counts, (135, 86, 161, 255))
    countMessage("Trace16", counts, (161, 85, 151, 255))
    countMessage("Buffer", counts, (146, 255, 99, 255))
    countMessage("And", counts, (255, 198, 99, 255))
    countMessage("Or", counts, (99, 242, 255, 255))
    countMessage("Xor", counts, (174, 116, 255, 255))
    countMessage("Not", counts, (255, 98, 138, 255))
    countMessage("Nand", counts, (255, 162, 0, 255))
    countMessage("Nor", counts, (48, 217, 255, 255))
    countMessage("Xnor", counts, (166, 0, 255, 255))
    countMessage("LatchOn", counts, (99, 255, 159, 255))
    countMessage("LatchOff", counts, (56, 77, 71, 255))
    countMessage("Clock", counts, (255, 0, 65, 255))
    countMessage("LED", counts, (255, 255, 255, 255))
    countMessage("Timer", counts, (255, 103, 0, 255))
    countMessage("Random", counts, (229, 255, 0, 255))
    countMessage("Break", counts, (224, 0, 0, 255))
    countMessage("Wifi0", counts, (255, 0, 191, 255))
    countMessage("Wifi1", counts, (255, 0, 175, 255))
    countMessage("Wifi2", counts, (255, 0, 159, 255))
    countMessage("Wifi3", counts, (255, 0, 143, 255))
    countMessage("Annotation", counts, (58, 69, 81, 255))
    countMessage("Filler", counts, (140, 171, 161, 255))
    if tracecount > 0:
        totalmessage.append("Trace pixels: " + str(tracecount) + percent(tracecount, bp.width * bp.height) + ", ")
    if buscount > 0:
        totalmessage.append("Bus pixels: " + str(buscount) + percent(tracecount, bp.width * bp.height) + ", ")
    totalmessage.append("Used area: " + str(area) + percent(area, bp.width * bp.height) + ", ")
    totalmessage.append("```")
    return totalmessage

def render(blueprint):

    def fillBackground(image, width, height):
        image = bytearray(image)
        for offset in range(0, 4*width*height, 4):
            if image[offset+3] == 0:
                image[offset+0] = 30
                image[offset+1] = 36
                image[offset+2] = 49
                image[offset+3] = 255
        return image

    def zoomImage(image, width, height, zoom):
        if zoom == 1:
            return image
        zimage = bytearray(4 * width * height * zoom * zoom)
        stride = 4 * width
        dststride = 4 * width * zoom
        for y in range(height):
            yo = y * stride
            for x in range(width):
                pixel = image[4 * x + yo : 4 * x + yo + 4]
                for dy in range(zoom):
                    dstyo = (y * zoom + dy) * dststride
                    for dx in range(zoom):
                        dsto = dstyo + 4 * (x * zoom + dx)
                        zimage[dsto] = pixel[0]
                        zimage[dsto+1] = pixel[1]
                        zimage[dsto+2] = pixel[2]
                        zimage[dsto+3] = pixel[3]
        return zimage

    def saveImage(filename, image, width, height, zoom):
        zoom = int(zoom)
        if zoom < 1:
            zoom = 1
        image = fillBackground(image, width, height)
        image = zoomImage(image, width, height, zoom)
        width *= zoom
        height *= zoom
        # split to arrays of rows.
        image = [image[i:i+4*width] for i in range(0, len(image), 4*width)]
        pngimage = png.from_array(image, "RGBA", {
            "width": width,
            "height": height,
            "bitdepth": 8
        })
        pngimage.save(filename)

    bp = parseBlueprint(blueprint)

    zoom = int(800 / bp.width)
    if zoom < 1:
        zoom = 1
    elif zoom > 16:
        zoom = 16
    saveImage("tempimage.png", bp.logicImage, bp.width, bp.height, zoom)

def time():
    time = str(datetime.datetime.utcnow()).replace(".",",")
    time = "[" + str(time[0:23]) + "]"
    return time

async def extractBlueprintString (ctx: commands.Context, args):
    """extract blueprint string from appropriate source"""
    blueprint = None
    # 1. first check for bp in args
    if len(args) >= 1:
        for text in args:
            if text.startswith("VCB+") or text.startswith("```VCB+"):
                blueprint = text
    # 2. if not found check for bp in attachment
    if blueprint == None and len(ctx.message.attachments) == 1:
        blueprint = (await ctx.message.attachments[0].read()).decode()
    # if not found, look in replied message...
    if blueprint == None and ctx.message.reference != None and ctx.message.reference.resolved != None:
        # 3. check reply content 
        if ctx.message.reference.resolved.content != "":
            for text in ctx.message.reference.resolved.content.split():
                if text.startswith("VCB+") or text.startswith("```VCB+"):
                    blueprint = text
        # 4. if still no blueprint found, then check attachment
        if blueprint == None and len(ctx.message.reference.resolved.attachments) == 1:
            blueprint = (await ctx.message.reference.resolved.attachments[0].read()).decode()
    return blueprint

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
    bot = CustomBot(prefix="!", activity=discord.Game(name='!help to learn more'))

    @bot.command(aliases=['hi'])
    async def hello(ctx: commands.Context, *args):
        """says hi :)"""
        print(time() + " INFO: user \"" + str(ctx.author.name) + "\" used: !hello / !hi")
        await ctx.send("hello! "+ str(ctx.author.mention))

    @bot.command(aliases=['statistics'])
    async def stats(ctx: commands.Context,  *blueprint):
        """
        makes a image of a blueprint

        Parameters
        ----------
        blueprint
             : any blueprint either a file or text (can reply to a meesage for a image of that blueprint aswell)
        """
        print(time() + " INFO: user \"" + str(ctx.author.name) + "\" used: !stats")
        # extract blueprint string from appropriate source
        blueprint = await extractBlueprintString(ctx, blueprint)
        # build stats/error message
        totalmessage = []
        if blueprint == None:
            totalmessage.append("no blueprint specified")
        else:
            try:
                totalmessage = getstats(blueprint)
            except Exception as x:
                totalmessage.append(str(x))
        # send the message
        await ctx.send(" ".join(totalmessage))

    @bot.command(aliases=['render'])
    @commands.has_permissions(attach_files=True)
    async def image(ctx: commands.Context, *blueprint):
        """
        makes a image of a blueprint

        Parameters
        ----------
        blueprint
             : any blueprint either a file or text (can reply to a meesage for a image of that blueprint aswell)
        """
        print(time() + " INFO: user \"" + str(ctx.author.name) + "\" used: !image")
        # extract blueprint string from appropriate source
        blueprint = await extractBlueprintString(ctx, blueprint)
        # render blueprint and send image
        totalmessage = []
        if blueprint == None:
            totalmessage.append("no blueprint specified")
        else:
            try:
                render(blueprint)
                await ctx.send(file=discord.File("tempimage.png"))
            except Exception as x:
                totalmessage.append(str(x))
        # send any error messages
        if totalmessage != []:
            await ctx.send(" ".join(totalmessage))

    @bot.command(aliases=['guide','manual'])
    async def rtfm(ctx: commands.Context, *question):
        """
        finds pages in the userguide based on a input

        Parameters
        ----------
        question
             : the thing you are looking for
        """
        print(time() + " INFO: user \"" + str(ctx.author.name) + "\" used: !rtfm "+" ".join(question))
        totalmessage = []
        guides = [
            "appendix blueprint specification",
            "assembly assembler",
            "assembly assembly language",
            "assembly bookmarks",
            "assembly expressions",
            "assembly external editing",
            "assembly macros 1",
            "assembly macros 2",
            "assembly origin directive",
            "assembly primitives labels",
            "assembly primitives numerics",
            "assembly primitives pointers",
            "assembly primitives symbols",
            "assembly primitives",
            "assembly review",
            "assembly statements 1",
            "assembly statements 2",
            "editing and simulating",
            "editing array tool",
            "editing blueprints",
            "editing edit mode tips",
            "editing filter",
            "editing layers",
            "editing simulation mode tips",
            "editing tools",
            "introduction editing and simulation",
            "introduction simulation engine",
            "user interface docking system",
            "user interface navigation and shortcuts",
            "user interface right click behavior",
            "virtual circuits annotation ink",
            "virtual circuits bus ink",
            "virtual circuits components and traces",
            "virtual circuits cross ink",
            "virtual circuits drawing based interface",
            "virtual circuits flow control 1",
            "virtual circuits flow control 2",
            "virtual circuits flow control 3",
            "virtual circuits flow control 4",
            "virtual circuits gate components",
            "virtual circuits general components 1",
            "virtual circuits general components 2",
            "virtual circuits mesh ink",
            "virtual circuits multiple io",
            "virtual circuits space optimization",
            "virtual circuits tunnel ink",
            "virtual circuits uncountable connection 1",
            "virtual circuits uncountable connection 2",
            "virtual devices virtual display",
            "virtual devices virtual input",
            "virtual devices virtual memory 1",
            "virtual devices virtual memory 2",
            "virtual devices virtual memory 3",
            "virtual devices",
        ]
        for item in guides:
            if " ".join(question).lower() in item:
                totalmessage.append(str(item))
        if question == ():
            await ctx.send("please provide a query")
        elif len(totalmessage) == 0:
            await ctx.send("sorry i couldnt find anything in the user guide")
        elif len(totalmessage) >= 16:
            await ctx.send("please be more specific")
        elif len(totalmessage) >= 5:
            matched = False
            question = "_".join(question).lower()
            for founditems in totalmessage:
                if question == founditems.replace(" ","_"):
                    await ctx.send(file=discord.File(founditems.replace(" ","_") + ".png"))
                    matched = True  
            if matched == False:
                await ctx.send("``` " + "\n ".join(totalmessage) + " ```")
        else:
            for image in totalmessage:
                await ctx.send(file=discord.File(image.replace(" ","_") + ".png"))

    bot.run()

if __name__ == "__main__":
    main()
