package tree

import (
	"iter"
)

type Tree []*Node

type Node struct {
	Data     map[string]string `json:"data,omitempty"`
	ParentId int               `json:"parent"`
}

func (t *Tree) Add(parent int, data map[string]string) *Node {
	node := &Node{Data: data, ParentId: parent}
	*t = append(*t, node)

	return node
}

func (t *Tree) Parent(node *Node) *Node {
	parent := node.ParentId

	return (*t)[parent]
}

func (t *Tree) Children(node *Node) iter.Seq[*Node] {
	parentIdx := t.IndexOf(node)

	return func(yield func(*Node) bool) {
		for _, n := range *t {
			if n.ParentId == parentIdx {
				if !yield(n) {
					return
				}
			}
		}
	}
}

func (t *Tree) Traverse(root *Node) iter.Seq[*Node] {
	return func(yield func(*Node) bool) {

		stack := []*Node{root}

		for len(stack) > 0 {
			// pop
			n := stack[len(stack)-1]
			stack = stack[:len(stack)-1]

			if !yield(n) {
				return
			}

			// collect children
			parentIdx := t.IndexOf(n)
			children := make([]*Node, 0)

			for _, c := range *t {
				if c.ParentId == parentIdx {
					children = append(children, c)
				}
			}

			// push in reverse so leftmost is visited first
			for i := len(children) - 1; i >= 0; i-- {
				stack = append(stack, children[i])
			}
		}
	}
}

func (t *Tree) IndexOf(node *Node) int {
	for i, n := range *t {
		if n == node {
			return i
		}
	}

	return -1
}
