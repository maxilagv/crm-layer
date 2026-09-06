from django.db import migrations
from pgvector.django import HnswIndex, VectorExtension, VectorField


def null_legacy_vectors(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        AIEmbedding = apps.get_model("ai", "AIEmbedding")
        for embedding in AIEmbedding.objects.all().iterator():
            vector = embedding.vector
            if not isinstance(vector, list) or len(vector) != 768:
                embedding.vector = None
                embedding.save(update_fields=["vector"])
        return

    table = schema_editor.quote_name("ai_embedding")
    column = schema_editor.quote_name("vector")
    schema_editor.execute(f"ALTER TABLE {table} ALTER COLUMN {column} DROP NOT NULL")
    schema_editor.execute(
        f"""
        UPDATE {table}
        SET {column} = NULL
        WHERE {column} IS NOT NULL
          AND (
            jsonb_typeof({column}) <> 'array'
            OR jsonb_array_length({column}) <> 768
          )
        """
    )
    schema_editor.execute(
        f"""
        ALTER TABLE {table}
        ALTER COLUMN {column} TYPE vector(768)
        USING CASE
          WHEN {column} IS NULL THEN NULL
          ELSE {column}::text::vector(768)
        END
        """
    )


class Migration(migrations.Migration):

    dependencies = [
        ("ai", "0008_alter_aievalcase_purpose_alter_aimodelconfig_purpose_and_more"),
    ]

    operations = [
        VectorExtension(),
        migrations.RunPython(null_legacy_vectors, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="aiembedding",
            name="vector",
            field=VectorField(blank=True, dimensions=768, null=True),
        ),
        migrations.AddIndex(
            model_name="aiembedding",
            index=HnswIndex(
                name="ai_embedding_vec_hnsw",
                fields=["vector"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ),
    ]
