#compdef quodlibet

local browsers=(SearchBar Playlists PanedBrowser AlbumList
CoverGrid AlbumCollection FileSystem InternetRadio AudioFeeds
Soundcloud)

local orders=(toggle inorder shuffle weighted onesong)

_arguments \
  '--add-location=[Add a file or directory to the library]:file or directory:_files'\
  '--debug[Print debugging information]'\
  '--enqueue=[Enqueue a file or query]:file or query:_files'\
  '--enqueue-files=[Enqueue comma-separated files]:files:_files'\
  '--filter=[Filter on a tag value]:key=value'\
  '--focus[Focus the running player]'\
  '--force-previous[Jump to previous song]'\
  '--help[Display brief usage information]'\
  '--hide-window[Hide main window]'\
  '--list-browsers[List available browsers]'\
  '--next[Jump to next song]'\
  '--no-plugins[Start without plugins]'\
  '--open-browser=[Open a new browser]:browser name:($browsers)'\
  '--pause[Pause playback]'\
  '--play[Start playback]'\
  '--play-file=[Play a file]:filename:_files'\
  '--play-pause[Toggle play/pause mode]'\
  '--previous[Jump to previous song]'\
  '--print-playing=[Print the playing song and exit]:pattern'\
  '--print-playlist[Print the current playlist]'\
  '--print-query[Print filenames of results of query to stdout]:query'\
  '--print-query-text[Print the active text query]'\
  '--print-queue[Print the contents of the queue]'\
  '--query=[Search your audio library]:query'\
  '--queue=[Show or hide the queue]:on|off|t:(on off t)'\
  '--quit[Exit Quod Libet]'\
  '--random=[Filter on a random value]:tag'\
  '--rating=[Set rating of playing song]:[+|-]0.0..1.0'\
  '--rating-down[Decrease rating of playing song by one star]'\
  '--rating-up[Increase rating of playing song by one star]'\
  '--refresh[Refresh and rescan library]'\
  '--repeat=[Turn repeat off, on, or toggle it]:0|1|t:(0 1 t)'\
  '--seek=[Seek within the playing song]:[+|-][HH\:]MM\:SS'\
  '--set-browser=[Set the current browser]:browser name:($browsers)'\
  '--show-window[Show main window]'\
  '--shuffle=[Set or toggle shuffle mode]:0|1|t:(0 1 t)'\
  '--shuffle-type=[Set shuffle mode type]:random|weighted|off:(random weighted off)'\
  "--start-hidden[Don't show any windows on start]"\
  '--start-playing[Begin playing immediately]'\
  '--status[Print player status]'\
  '--stop[Stop playback]'\
  '--stop-after=[Stop after the playing song]:0|1|t:(0 1 t)'\
  '--toggle-window[Toggle main window visibility]'\
  '--unfilter[Remove active browser filters]'\
  '--version[Display version and copyright]'\
  '--volume=[Set the volume]:[+|-]0..100'\
  '--volume-down[Turn down volume]'\
  '--volume-up[Turn up volume]'\
  '--with-pattern=[Set template for --print-* commands]:pattern'
