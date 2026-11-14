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
as ``gold``. ``read()`` qualifies that table with the dataset id, rejects a
statement that names another dataset, and posts it to ``POST /query/``.
``FetchQueryDeserializer`` turns each response into a frame, and ``read()``
concatenates truncated pages into ``output``. A failure keeps those pages
and stores the next offset in ``checkpoint["pagination"]``. A finished
read clears that entry.

``list()`` pages through ``GET /dataset/``.

``create``, ``update``, ``upsert``, ``delete``, ``purge``, and ``rename``
raise ``NotSupportedError``. ``serializer`` is ``None``.

Examples
--------

Copy ``.env.example`` to ``.env``. The scripts construct the linked service
and dataset directly.

.. code-block:: bash

   uv run --extra dev python examples/03_dataset_gold_read.py
