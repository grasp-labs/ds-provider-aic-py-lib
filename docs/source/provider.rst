AIC provider
============

The identity linked service sets AIC defaults on the HTTP protocol.
The protocol performs client-credentials and username/password sign-in.
The gold dataset posts SQL to the fetch API and does not write.

Identity linked service
-----------------------

``AICIdentityLinkedService`` is an ``HttpLinkedService``.

* ``auth_type="Bearer"`` posts ``username`` and ``password`` to
  ``https://auth.grasp-daas.com/auth/login/``. ``username`` is the account email.
* ``auth_type="OAuth2"`` uses client credentials against
  ``https://auth.grasp-daas.com/oauth/token/``. The token request sends
  ``client_id``, ``client_secret``, ``scope``, and ``grant_type``.

``connect()`` and ``test_connection()`` are the HTTP protocol methods.

Gold dataset
------------

``AICGoldDataset`` stores the published definition: ``publish_mode``,
``primary_key_fields``, ``ordering_field``, ``delete_field``, ``history_mode``,
and ``partition_keys``. Those fields are not applied as writes.

``read()`` requires ``settings.read.sql``. The statement names this dataset
as ``gold``. ``read()`` rewrites that name to this dataset id. A quoted
reference to another dataset is rejected here. Any other name is left to
the caller's fetch grants. The statement is posted to ``POST /query/``.
``FetchQueryDeserializer`` turns each response into a frame, and ``read()``
concatenates truncated pages into ``output``. A result that can span more
than one page needs ``ORDER BY`` so later ``OFFSET`` pages stay in the same
order. A failure keeps the pages read in that call and stores the next
offset in ``checkpoint["pagination"]``. A truncated page with no rows to
continue from raises ``ReadError`` and leaves that checkpoint in place. A
finished read clears it.

``list()`` pages through ``GET /dataset/``.

``create``, ``update``, ``upsert``, ``delete``, ``purge``, and ``rename``
raise ``NotSupportedError``. ``serializer`` is ``None``.

Examples
--------

Copy ``.env.example`` to ``.env``. The scripts construct the linked service
and dataset directly.

.. code-block:: bash

   uv run --extra dev python examples/03_dataset_gold_read.py
