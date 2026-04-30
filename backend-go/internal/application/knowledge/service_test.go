package knowledge

import (
	"context"
	"errors"
	"testing"
	"time"
)

func TestListNodesNormalizesPaginationAndFilters(t *testing.T) {
	repo := &fakeKnowledgeRepo{
		count: 21,
		nodes: []KnowledgeNode{{ID: "node-1", Name: "极限", NodeType: "concept"}},
	}
	service := newKnowledgeTestService(repo, time.Now())

	response, err := service.ListNodes(context.Background(), NodeFilter{Page: -1, PageSize: 500, NodeType: "CONCEPT", Search: " 极限 "})
	if err != nil {
		t.Fatalf("ListNodes() error = %v", err)
	}
	if response.Page != 1 || response.PageSize != 100 || response.TotalPages != 1 || len(response.Items) != 1 {
		t.Fatalf("response = %#v", response)
	}
	if repo.lastFilter.NodeType != "concept" || repo.lastFilter.Search != "极限" {
		t.Fatalf("filter = %#v", repo.lastFilter)
	}
}

func TestCreateNodeValidatesTypeAndPersistsDefaults(t *testing.T) {
	now := time.Date(2026, time.April, 27, 10, 0, 0, 0, time.UTC)
	repo := &fakeKnowledgeRepo{createdNode: KnowledgeNode{ID: "node-1", Name: "极限", NodeType: "concept"}}
	service := newKnowledgeTestService(repo, now)

	if _, err := service.CreateNode(context.Background(), NodeInput{Name: "bad", NodeType: "bad"}); !errors.Is(err, ErrBadRequest) {
		t.Fatalf("CreateNode(invalid) error = %v, want ErrBadRequest", err)
	}

	response, err := service.CreateNode(context.Background(), NodeInput{Name: " 极限 ", NodeType: "CONCEPT", Difficulty: 0.5})
	if err != nil {
		t.Fatalf("CreateNode() error = %v", err)
	}
	if !response.Success || response.Message != "创建成功" || response.Node == nil || response.Node.ID != "node-1" {
		t.Fatalf("response = %#v", response)
	}
	if repo.lastNodeInput.Name != "极限" || repo.lastNodeInput.NodeType != "concept" || !repo.lastNow.Equal(now) {
		t.Fatalf("input=%#v now=%v", repo.lastNodeInput, repo.lastNow)
	}
}

func TestUpdateNodeRejectsEmptyAndMapsMissing(t *testing.T) {
	repo := &fakeKnowledgeRepo{}
	service := newKnowledgeTestService(repo, time.Now())

	if _, err := service.UpdateNode(context.Background(), "node-1", NodeUpdate{}); !errors.Is(err, ErrBadRequest) {
		t.Fatalf("UpdateNode(empty) error = %v, want ErrBadRequest", err)
	}
	name := "极限"
	if _, err := service.UpdateNode(context.Background(), "node-1", NodeUpdate{Name: &name}); !errors.Is(err, ErrNotFound) {
		t.Fatalf("UpdateNode(missing) error = %v, want ErrNotFound", err)
	}

	repo.updatedOK = true
	repo.updatedNode = KnowledgeNode{ID: "node-1", Name: "极限", NodeType: "concept"}
	response, err := service.UpdateNode(context.Background(), "node-1", NodeUpdate{Name: &name})
	if err != nil {
		t.Fatalf("UpdateNode() error = %v", err)
	}
	if response.Node == nil || response.Node.Name != "极限" {
		t.Fatalf("response = %#v", response)
	}
}

func TestCreateRelationValidatesNodesAndRelationType(t *testing.T) {
	repo := &fakeKnowledgeRepo{nodeExists: map[string]bool{"source": true}}
	service := newKnowledgeTestService(repo, time.Now())

	_, err := service.CreateRelation(context.Background(), RelationInput{SourceID: "source", TargetID: "missing", RelationType: "used_in"})
	if !errors.Is(err, ErrBadRequest) || err.Error() != "目标节点不存在" {
		t.Fatalf("CreateRelation(missing target) error = %v", err)
	}

	repo.nodeExists["target"] = true
	repo.createdRelation = KnowledgeRelation{ID: "rel-1", SourceID: "source", TargetID: "target", RelationType: "used_in"}
	response, err := service.CreateRelation(context.Background(), RelationInput{SourceID: " source ", TargetID: "target", RelationType: "USED_IN", Weight: 0.8})
	if err != nil {
		t.Fatalf("CreateRelation() error = %v", err)
	}
	if response.Relation == nil || response.Relation.ID != "rel-1" || repo.lastRelationInput.RelationType != "used_in" {
		t.Fatalf("response=%#v input=%#v", response, repo.lastRelationInput)
	}
}

func TestDeleteRelationMapsMissing(t *testing.T) {
	service := newKnowledgeTestService(&fakeKnowledgeRepo{}, time.Now())
	if _, err := service.DeleteRelation(context.Background(), "rel-1"); !errors.Is(err, ErrNotFound) {
		t.Fatalf("DeleteRelation() error = %v, want ErrNotFound", err)
	}
}

func newKnowledgeTestService(repo *fakeKnowledgeRepo, now time.Time) *Service {
	service, err := NewService(repo)
	if err != nil {
		panic(err)
	}
	service.now = func() time.Time { return now }
	return service
}

type fakeKnowledgeRepo struct {
	stats              Stats
	chapters           []string
	count              int
	nodes              []KnowledgeNode
	simpleNodes        []SimpleNode
	node               KnowledgeNode
	nodeFound          bool
	createdNode        KnowledgeNode
	updatedNode        KnowledgeNode
	updatedOK          bool
	deleteNodeOK       bool
	nodeExists         map[string]bool
	relations          []KnowledgeRelation
	createdRelation    KnowledgeRelation
	updatedRelation    KnowledgeRelation
	updatedRelationOK  bool
	deleteRelationOK   bool
	lastFilter         NodeFilter
	lastNodeInput      NodeInput
	lastNodeUpdate     NodeUpdate
	lastRelationInput  RelationInput
	lastRelationUpdate RelationUpdate
	lastNow            time.Time
}

func (r *fakeKnowledgeRepo) Stats(context.Context) (Stats, error) {
	return r.stats, nil
}

func (r *fakeKnowledgeRepo) DistinctChapters(context.Context) ([]string, error) {
	return r.chapters, nil
}

func (r *fakeKnowledgeRepo) CountNodes(_ context.Context, filter NodeFilter) (int, error) {
	r.lastFilter = filter
	return r.count, nil
}

func (r *fakeKnowledgeRepo) ListNodes(_ context.Context, filter NodeFilter) ([]KnowledgeNode, error) {
	r.lastFilter = filter
	return r.nodes, nil
}

func (r *fakeKnowledgeRepo) ListAllSimpleNodes(context.Context) ([]SimpleNode, error) {
	return r.simpleNodes, nil
}

func (r *fakeKnowledgeRepo) GetNode(context.Context, string) (KnowledgeNode, bool, error) {
	return r.node, r.nodeFound, nil
}

func (r *fakeKnowledgeRepo) CreateNode(_ context.Context, input NodeInput, now time.Time) (KnowledgeNode, error) {
	r.lastNodeInput = input
	r.lastNow = now
	return r.createdNode, nil
}

func (r *fakeKnowledgeRepo) UpdateNode(_ context.Context, _ string, update NodeUpdate, now time.Time) (KnowledgeNode, bool, error) {
	r.lastNodeUpdate = update
	r.lastNow = now
	return r.updatedNode, r.updatedOK, nil
}

func (r *fakeKnowledgeRepo) DeleteNode(context.Context, string) (bool, error) {
	return r.deleteNodeOK, nil
}

func (r *fakeKnowledgeRepo) NodeExists(_ context.Context, nodeID string) (bool, error) {
	return r.nodeExists[nodeID], nil
}

func (r *fakeKnowledgeRepo) ListRelations(context.Context, string) ([]KnowledgeRelation, error) {
	return r.relations, nil
}

func (r *fakeKnowledgeRepo) CreateRelation(_ context.Context, input RelationInput, now time.Time) (KnowledgeRelation, error) {
	r.lastRelationInput = input
	r.lastNow = now
	return r.createdRelation, nil
}

func (r *fakeKnowledgeRepo) UpdateRelation(_ context.Context, _ string, update RelationUpdate) (KnowledgeRelation, bool, error) {
	r.lastRelationUpdate = update
	return r.updatedRelation, r.updatedRelationOK, nil
}

func (r *fakeKnowledgeRepo) DeleteRelation(context.Context, string) (bool, error) {
	return r.deleteRelationOK, nil
}
