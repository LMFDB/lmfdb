
class inventory_data:
  def init(self, database, collection, data, orphans):
    self.database = database
    self.collection = collection
    self.data = data
    self.orphans = orphans

  def rename_key(self, previous, new):
    try:
	    key_data = self.orphans[previous]
	    self.data[new] = key_data
    except:
      pass

  def get_outdated_keys(self):
	  return self.orphans.__keys__

