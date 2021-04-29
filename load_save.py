
def load_save(bot):
    try:
        global Guild_settings
        global Global_chat
        global Global_mute
        global Official_emojis
        global Number_emojis
        global Waveclient, Dissoku_alerts
        global Sevennet_channels
        global Sevennet_posts
        global Favorite_songs
        global Private_chats
        global Private_chat_pass
        global Private_chat_author
        global Bump_alerts
        global GBan, Afks
        global Blacklists
        global Levelup_off, Command_counter, SB_Bans, Queues, Channels, Role_list, Instant_leave

        tmp_gs = bot.raw_config
        SB_Bans = tmp_gs["sbb"]
        Guild_settings = tmp_gs["gs"]
        Global_chat = tmp_gs["gc"]
        Global_mute = tmp_gs["gm"]
        Instant_leave = tmp_gs["il"]
        GBan = tmp_gs["gb"]
        Private_chats = tmp_gs["pc"]
        Private_chat_pass = tmp_gs["pp"]
        Private_chat_author = tmp_gs["pa"]
        Role_list = tmp_gs["rl"]
        Sevennet_channels = tmp_gs["snc"]
        Sevennet_posts = tmp_gs["snp"]
        Favorite_songs = tmp_gs["fs"]
        Bump_alerts = tmp_gs["ba"]
    #             Dissoku_alerts=tmp_gs["da"]
        Dissoku_alerts = tmp_gs["da"]
        Blacklists = tmp_gs["bs"]
        Levelup_off = tmp_gs["lo"]
        Command_counter = tmp_gs["cc"]
        Queues = bot.consts["qu"]
        Channels = bot.consts["ch"]
        Official_emojis = bot.consts["oe"]
        Number_emojis = bot.consts["ne"]
    except Exception as e:
        print("load_save error:" + e)
        raise e
