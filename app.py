from jina import Flow, Document, DocumentArray

# from jina.parsers.helloworld import set_hw_chatbot_parser
import click
from config import port, workdir, datafile, max_docs, random_seed, model
from helper import deal_with_workspace

try:
    __import__("pretty_errors")
except ImportError:
    pass

flow = (
    Flow()
    .add(
        name="text_encoder",
        uses="jinahub+docker://TransformerTorchEncoder",
        uses_with={"max_length": 50},
        # uses_with={"pretrained_model_name_or_path": model, "max_length": 50},
    )
    .add(
        uses="jinahub+docker://SimpleIndexer",
        uses_with={"index_file_name": "index", "default_top_k": 12},
        uses_metas={"workspace": "workspace"},
        name="text_indexer",
        volumes="./workspace:/workspace/workspace",
    )
)


def prep_docs(input_file, num_docs=None, shuffle=True):
    import json

    docs = DocumentArray()
    memes = []
    print(f"Processing {input_file}")
    with open(input_file, "r") as file:
        raw_json = json.loads(file.read())

    for template in raw_json:
        for meme in template["generated_memes"]:
            meme["template"] = template["name"]
        memes.extend(template["generated_memes"])

    if shuffle:
        import random

        random.seed(random_seed)
        random.shuffle(memes)

    for meme in memes[:num_docs]:
        doctext = f"{meme['template']} - {meme['caption_text']}"
        doc = Document(text=doctext)
        doc.tags = meme
        doc.tags["uri_absolute"] = "http" + doc.tags["image_url"]
        docs.extend([doc])

    return docs


def index(num_docs: int = max_docs):
    """
    Build an index for your search
    :param num_docs: maximum number of Documents to index
    """
    with flow:
        flow.post(
            on="/index",
            inputs=prep_docs(input_file=datafile, num_docs=num_docs),
            request_size=64,
            read_mode="r",
        )


def query_restful():
    """
    Query your index
    """
    with flow:
        flow.protocol = "http"
        flow.port_expose = port
        flow.block()


@click.command()
@click.option(
    "--task",
    "-t",
    type=click.Choice(["index", "query_restful"], case_sensitive=False),
)
@click.option("--num_docs", "-n", default=max_docs)
@click.option("--force", "-f", is_flag=True)
def main(task: str, num_docs: int, force: bool):
    if task == "index":
        deal_with_workspace(dir_name=workdir, should_exist=False, force_remove=force)
        index(num_docs=num_docs)

    if task == "query_restful":
        deal_with_workspace(dir_name=workdir, should_exist=True)
        query_restful()


if __name__ == "__main__":
    main()
