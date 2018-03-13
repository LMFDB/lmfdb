import json
import inventory_live_data as ild

def act(request):
    """Unpack requested action and trigger it

    Available actions:
    mark_gone -- mark any collections that are gone (no longer in live db)
    clean_gone -- clean up any collections which are marked 'gone'

    clean_scrapes -- Clean up any bad scrapes (i.e old but not complete)
    """
    request = json.loads(request)
    print request
    action = request['action']
    #action = request['action']
    result = None
    reply = None
    data = None
    if action == 'mark_gone':
        result = ild.update_gone_list()
    elif action == 'clean_gone':
        #result = ild.remove_gone_collections()
        result = False
        reply = 'Action TBC'
    elif action == 'clean_scrapes':
        result = False
        reply = 'Action TBA'
    elif action == 'download_orphans':
        data = ild.collate_orphans()
        reply = 'Downloading Data'
        result = True
    else:
        return {'err':True, 'reply':'Requsted action not understood', 'data':data}

    if reply is None:
        if result:
            reply = 'Operation succesful'
        else:
            reply = 'Unknown error occurred'

    return {'err': not result, 'reply':reply, 'data':data}
