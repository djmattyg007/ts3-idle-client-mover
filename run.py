#!/usr/bin/python3

from collections import defaultdict, namedtuple
import configargparse
from dataclasses import dataclass, field
from humanfriendly import format_timespan
import sys
import ts3


__version__ = "2.0.0"


@dataclass(frozen=True)
class Client(object):
    clid: int
    cid: int
    dbid: int
    nickname: str = field(compare=False)
    idle_time: int = field(compare=False)


parser = configargparse.ArgumentParser(
    prog="TS3 Idle Client Mover",
    auto_env_var_prefix="TS3ICM_",
    default_config_files=[
        "/etc/teamspeak-utils/idle-client-mover.conf",
        "/etc/teamspeak-utils/idle-client-mover/*.conf",
        "~/.config/teamspeak-utils/idle-client-mover.conf",
        "~/.config/teamspeak-utils/idle-client-mover/*.conf",
        "./idle-client-mover.conf",
    ],
    args_for_setting_config_path=["-c", "--config"],
    ignore_unknown_config_file_keys=True
)
parser.add("--version", action="version", version="%(prog)s {0}".format(__version__))
parser.add("--sq-hostname", action="store", type=str, required=True)
parser.add("--sq-port", action="store", type=int, required=False, default=10022)
parser.add("--sq-username", action="store", type=str, required=True)
parser.add("--sq-password", action="store", type=str, required=True)
parser.add("--server-id", action="store", type=int, required=False, default=1)
parser.add("--afk-channel-id", action="store", type=int, required=True)
parser.add("--idle-time", action="store", type=int, required=True)
parser.add("--ignore-client", action="append", type=int, required=False, default=[], dest="ignore_clients")
parser.add("--special-client", action="append", type=str, required=False, default=[], dest="special_clients")

args = parser.parse_args()
formatted_idle_time = format_timespan(args.idle_time)

special_clients = dict()
for special in args.special_clients:
    dbid, cid = special.split(sep="=", maxsplit=1)
    special_clients[int(dbid)] = int(cid)


with ts3.query.TS3ServerConnection() as conn:
    try:
        conn.open(args.sq_hostname, args.sq_port, protocol="ssh", tp_args={
            "username": args.sq_username,
            "password": args.sq_password,
            "load_system_host_keys": True,
        })
    except ts3.common.TS3Error as e:
        sys.stderr.write("Connection failed: {0}\n".format(e))
        sys.exit(1)

    conn.exec_("use", sid=args.server_id)

    resp = conn.query("clientlist", "times").fetch()

    channel_counts = defaultdict(int)
    client_move_requests = dict()

    for client_data in resp.parsed:
        if int(client_data["client_type"]) != 0:
            # If not a regular user
            continue

        client = Client(
            clid=int(client_data["clid"]),
            cid=int(client_data["cid"]),
            dbid=int(client_data["client_database_id"]),
            nickname=client_data["client_nickname"],
            # The server returns the idle time in milliseconds
            idle_time=(int(client_data["client_idle_time"]) // 1000),
        )
        channel_counts[client.cid] += 1

        dest_channel_id = args.afk_channel_id
        if client.dbid in special_clients:
            dest_channel_id = special_clients[client.dbid]

        if client.cid == dest_channel_id:
            # If the client is already in their destination channel
            continue
        elif client.dbid in args.ignore_clients:
            # If we're ignoring this client
            continue

        if client.idle_time < args.idle_time:
            # User's idle time is under the max idle time
            continue

        client_move_requests[client] = dest_channel_id

    for client, dest_channel_id in client_move_requests.items():
        # Don't move the user if the channel they're in has at least one other user in it
        if channel_counts[client.cid] > 1 and client.cid != args.afk_channel_id:
            continue

        # TODO: Use logging module, better integrate with journal
        sys.stdout.write("Moving AFK client {0} to channel {1}\n".format(repr(client), dest_channel_id))

        msg = "You have been moved to AFK after being idle for more than {0}.".format(formatted_idle_time)
        conn.exec_("sendtextmessage", targetmode=1, target=client.clid, msg=msg)
        conn.exec_("clientmove", clid=client.clid, cid=dest_channel_id)

    conn.close()
