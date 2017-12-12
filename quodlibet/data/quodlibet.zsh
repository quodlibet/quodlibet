#compdef quodlibet

local browsers='(SearchBar Playlists PanedBrowser AlbumList '\
'FileSystem InternetRadio AudioFeeds MediaDevices)'

local orders='(toggle inorder shuffle weighted onesong)'

_arguments \
  '--enqueue=[Enqueue a file or query]:file or query:_files'\
  '--filter=[Filter on a tag value]:key=value'\
  '--focus[Focus the running player]'\
  '--force-previous[Jump to previous song]'\
  '--hide-window[Hide main window]'\
  '--next[Jump to next song]'\
  '--open-browser=[Open a new browser]:browser name:'$browsers\
  '--order=[Set or toggle the playback order]:order or toggle:'$orders\
  '--pause[Pause playback]'\
  '--play[Start playback]'\
  '--play-file=[Play a file]:filename:_files'\
  '--play-pause[Toggle play/pause mode]'\
  '--previous[Jump to previous song]'\
  '--print-playing=[Print the playing song and exit]:pattern'\
  '--print-playlist[Print the current playlist]'\
  '--print-queue[Print the contents of the queue]'\
  '--query[Search your audio library]'\
  '--queue=[Show or hide the queue]:on|off|t:(on off t)'\
  '--quit[Exit Quod Libet]'\
  '--random=[Filter on a random value]:tag'\
  '--refresh[Refresh and rescan library]'\
  '--repeat=[Turn repeat off, on, or toggle it]:0|1|t:(0 1 t)'\
  '--seek=[Seek within the playing song]:[+|-][HH\:]MM\:SS'\
  '--set-browser=[Set the current browser]:browser name:'$browsers\
  '--set-rating=[Rate the playing song]:0.0..1.0'\
  '--show-window[Show main window]'\
  '--song-list=[Show or hide the main song list]:on|off|t:(on off t)'\
  '--start-playing[Begin playing immediately]'\
  '--status[Print player status]'\
  '--toggle-window[Toggle main window visibility]'\
  '--unfilter[Remove active browser filters]'\
  '--volume=[Set the volume]:(+|-|)0..100'\
  '--volume-down[Turn down volume]'\
  '--volume-up[Turn up volume]'
