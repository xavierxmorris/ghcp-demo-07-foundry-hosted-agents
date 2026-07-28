"""Tests for the docs-qa retrieval layer.

The critical behaviour is the *negative* case: an off-topic question must return
nothing, so the agent can decline instead of hallucinating a citation.
"""

from __future__ import annotations

import pytest

import retrieval


class TestTokenization:
    def test_stopwords_are_removed(self):
        assert "the" not in retrieval.tokenize("the refund window")
        assert "refund" in retrieval.tokenize("the refund window")

    def test_lowercases_and_strips_punctuation(self):
        assert retrieval.tokenize("Policy!") == ["policy"]

    def test_plurals_and_participles_are_stemmed_together(self):
        assert retrieval.tokenize("refund") == retrieval.tokenize("refunds")
        assert retrieval.tokenize("refund") == retrieval.tokenize("refunded")
        assert retrieval.tokenize("chargeback") == retrieval.tokenize("chargebacks")


class TestCorpus:
    def test_corpus_is_discovered(self):
        docs = retrieval.list_documents()
        assert "refunds-policy" in docs
        assert len(docs) >= 5

    def test_documents_are_chunked_by_heading(self):
        chunks, _, _ = retrieval._index()
        sections = {chunk.section for chunk in chunks if chunk.doc_id == "refunds-policy"}
        assert "Partial refunds" in sections
        assert "Refund failures" in sections

    def test_every_chunk_has_a_citation(self):
        chunks, _, _ = retrieval._index()
        assert all("#" in chunk.citation for chunk in chunks)


class TestSearch:
    @pytest.mark.parametrize(
        ("query", "expected_doc"),
        [
            ("how long do I have to refund a payment", "refunds-policy"),
            ("how many times can I partially refund", "refunds-policy"),
            ("what happens when a webhook delivery fails", "webhooks"),
            ("how do I verify the webhook signature", "webhooks"),
            ("how do I rotate an API key", "api-authentication"),
            ("what is the rate limit", "api-authentication"),
            ("when do funds reach my bank account", "settlement-and-payouts"),
            ("how long to respond to a Visa chargeback", "chargebacks-and-disputes"),
            ("does Contoso support Apple Pay", "payment-methods"),
        ],
    )
    def test_relevant_document_is_retrieved(self, query, expected_doc):
        results = retrieval.search(query, top_k=3)
        assert results, f"no results for {query!r}"
        assert expected_doc in {hit["doc_id"] for hit in results}

    def test_results_are_sorted_by_relevance(self):
        results = retrieval.search("refund settlement timing", top_k=5)
        scores = [hit["relevance"] for hit in results]
        assert scores == sorted(scores, reverse=True)

    def test_top_k_is_respected_and_clamped(self):
        assert len(retrieval.search("refund", top_k=2)) <= 2
        assert len(retrieval.search("refund", top_k=999)) <= 10

    @pytest.mark.parametrize(
        "query",
        [
            "who won the 1998 football world cup",
            "what is the capital of Australia",
            "how do I roast a chicken",
            "explain quantum entanglement",
        ],
    )
    def test_off_topic_query_returns_nothing(self, query):
        # This is what lets the agent say "I don't know" instead of guessing.
        # Note "won" and "capital" do appear in the corpus -- a single
        # incidental term must not be enough to produce a citable hit.
        assert retrieval.search(query) == []

    def test_empty_and_stopword_only_queries_return_nothing(self):
        assert retrieval.search("") == []
        assert retrieval.search("the and of") == []

    def test_search_is_deterministic(self):
        assert retrieval.search("dispute deadline", top_k=3) == retrieval.search(
            "dispute deadline", top_k=3
        )


class TestFetchDocument:
    def test_fetch_returns_full_document(self):
        result = retrieval.get_document("webhooks")
        assert result["found"] is True
        assert "Signature verification" in result["content"]

    def test_unknown_document_lists_available_ones(self):
        result = retrieval.get_document("does-not-exist")
        assert result["found"] is False
        assert "webhooks" in result["available"]

    def test_path_traversal_is_neutralised(self):
        result = retrieval.get_document("../../../../etc/passwd")
        assert result["found"] is False
