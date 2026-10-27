COMPONENTS = {
 'component-1-general': {'label':'Component 1', 'name':'Religion, philosophy & ethics','minutes':120,'sections':[(1,'Issues of Relationships','theme-1-relationships'),(2,'Issues of Life and Death','theme-2-life-and-death'),(3,'Issues of Good and Evil','theme-3-good-and-evil'),(4,'Issues of Human Rights','theme-4-human-rights')]},
 'component-2-christianity': {'label':'Component 2','name':'Christianity','minutes':60,'sections':[(1,'Beliefs and Teachings','shared-beliefs-and-practices'),(2,'Practices','shared-beliefs-and-practices')]},
 'component-3-islam': {'label':'Component 3','name':'Islam','minutes':60,'sections':[(1,'Beliefs and Teachings','option-3-shared-beliefs-and-practices'),(2,'Practices','option-3-shared-beliefs-and-practices')]},
}
COMPONENT_CHOICES = [(k,v['label']+' · '+v['name']) for k,v in COMPONENTS.items()]
MARKS = {'b':5,'c':8,'d':15}

def rubric_id(component, part, number):
    if part=='c' and component=='component-1-general': return 'eduqas_c_8mark_ao1_component1'
    if part=='d' and component=='component-1-general' and number==2: return 'eduqas_d_15mark_ao2_c1_q2'
    return {'b':'eduqas_b_5mark_ao1','c':'eduqas_c_8mark_ao1','d':'eduqas_d_15mark_ao2'}[part]

def spag_eligible(component, part, number):
    return component in ('component-1-general','component-2-christianity') and part=='d' and number==1
