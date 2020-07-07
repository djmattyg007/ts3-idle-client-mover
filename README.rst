=====================
TS3 Idle Client Mover
=====================

Teamspeak stores a lot of timing information about each client, including how
long the client has been idle for (down to the millisecond). This script uses
that information to determine if a client is idle.

If a client has been idle for longer than the configurable threshold
(``--idle-time``), and the channel they're in has no other clients in it, the
client will be moved to the designated AFK channel (``--afk-channel-id``).

It is possible to tell this script to permanently ignore specific clients, to
prevent them from being considered idle. Pass the ``--ignore-client`` flag once
for each client.

It is also possible to designate different AFK channels on a per-client basis,
using the ``--special-client`` flag. Pass this flag once for each relevant
client, using the form ``{client_database_id}:{channel_id}`` where ``channel_id``
is the channel that client should be moved to.
